from typing import (
    Collection,
    Optional
)

from django.contrib import (
    admin,
    messages
)
from django.contrib.admin.utils import flatten_fieldsets
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseRedirect
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions

from django_banking.admin.base import DisplayUserMixin
from django_banking.admin.helpers import get_link_tag
from jibrel.core.common.helpers import get_bad_request_response
from jibrel.kyc.exceptions import BadTransitionError
from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)
from jibrel_admin.celery import force_onfido_routine

from ..signals import (
    kyc_approved,
    kyc_rejected
)
from .forms import (
    IndividualKYCSubmissionForm,
    OrganizationKYCSubmissionForm,
    RejectKYCSubmissionForm
)
from .inlines import (
    BeneficiaryInline,
    DirectorInline,
    PrincipalAddressInline,
    RegistrationAddressInline
)


@admin.register(IndividualKYCSubmission)
class IndividualKYCSubmissionModelAdmin(DisplayUserMixin, DjangoObjectActions, admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = IndividualKYCSubmissionForm

    ordering = ('-created_at',)

    search_fields = ('profile__user__email', 'profile__user__uuid')

    list_display = (
        '__str__', 'status', 'onfido_result', 'created_at'
    )

    radio_fields = {'status': admin.VERTICAL}
    fieldsets_reject = (
        (None, {
            'fields': (
                'reject_reason',
            )
        }),
    )

    always_readonly_fields = [
        'onfido_applicant_id',
        'onfido_check_id',
        'onfido_result',
        'onfido_report',
        'status',
        'created_at',
        'transitioned_at',
        'user_link',
    ]

    def get_fieldsets(self, request, obj=None):
        if self.__is_reject_form__(request, obj):
            return self.fieldsets_reject
        return (
            (None, {
                'fields': (
                    'account_type',
                    'status',
                )
            }),
            ('profile', {
                'fields': (
                    'user_link' if obj else 'profile',
                    ('first_name', 'middle_name', 'last_name',),
                    'birth_date',
                    'nationality',
                )
            }),
            ('Current Residential Address', {
                'fields': (
                    'country',
                    'city',
                    'post_code',
                    ('street_address', 'apartment',),
                )
            }),
            ('Income Information', {
                'fields': (
                    'occupation',
                    'income_source',
                ),
            }),
            ('Documentation', {
                'fields': (
                    'passport_number',
                    'passport_expiration_date',
                    'passport_document__file',
                    'proof_of_address_document__file'
                )
            }),
            ('onfido', {
                'fields': (
                    'onfido_applicant_id',
                    'onfido_check_id',
                    'onfido_result',
                    'onfido_report',
                ),
                'classes': ('collapse',),
            }),
            ('Submission', {
                'fields': (
                    'admin_note',
                    'reject_reason',
                )
            }),
            (_('Important dates'), {
                'fields': (
                    'created_at',
                    'transitioned_at'
                )
            }),
        )

    @staticmethod
    def _get_user(obj):
        return obj.profile.user

    def get_change_actions(self, request, object_id, form_url):
        actions = super().get_change_actions(request, object_id, form_url)
        # approve and reject is not available, if status is deffer from DRAFT
        # to avoid extra operations filter is using instead objects.get
        try:
            status = self.model.objects.filter(pk=object_id).only('status')[0].status
            exclude = {
                'approved': {'approve'},
                'rejected': {'reject'},
            }.get(status, set())
            return set(actions) - exclude
        except IndexError:
            return actions

    def __is_reject_form__(self, request, obj):
        return obj and request.path == reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_actions', kwargs={
            'pk': obj.pk,
            'tool': 'reject'
        })

    def get_readonly_fields(self, request: HttpRequest, obj: BaseKYCSubmission = None) -> Collection[str]:

        if not obj:
            return self.always_readonly_fields
        if obj.is_draft:
            return self.always_readonly_fields + [
                'profile',
                'account_type',
            ]
        elif self.__is_reject_form__(request, obj):
            return []

        all_fields = set(flatten_fieldsets(self.get_fieldsets(request, obj)))
        # reject reason can be changed only if it not changed before
        if obj and not obj.reject_reason:
            all_fields = all_fields - {'reject_reason'}

        # TODO
        # https://code.djangoproject.com/ticket/29682
        return all_fields - {
            'admin_note',
            'passport_document__file',
            'proof_of_address_document__file',
            'commercial_register__file',
            'shareholder_register__file',
            'articles_of_incorporation__file'
        }

    def get_form(self, request, obj=None, change=False, **kwargs):
        defaults = {}
        if self.__is_reject_form__(request, obj):
            defaults['form'] = RejectKYCSubmissionForm
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def approve(self, request: HttpRequest, obj: BaseKYCSubmission) -> Optional[HttpResponseBadRequest]:
        if obj.is_approved():
            self.message_user(request, 'Approved already', level=messages.SUCCESS)
            return
        try:
            obj.approve()
            self.after_approve_hook(request, obj)
            self.message_user(request, 'Approved', level=messages.SUCCESS)
        except BadTransitionError:
            return get_bad_request_response('Transition restricted')

    def clone(self, request: HttpRequest, obj: BaseKYCSubmission) -> HttpResponseBadRequest:
        clone_ = obj.clone()
        return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=clone_.pk)

    def reject(self, request: HttpRequest, obj: BaseKYCSubmission):
        if obj.is_rejected():
            self.message_user(request, 'Rejected already')
            return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)

        form = RejectKYCSubmissionForm(request.POST, instance=obj)
        if request.method == 'POST' and form.is_valid():
            # save reject reason
            form.save()
            try:
                obj.reject()
                self.after_reject_hook(request, obj)
                self.message_user(request, 'Rejected')
            except BadTransitionError:
                messages.add_message(request, messages.ERROR, 'Transition restricted')
            return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)
        return self.changeform_view(request, object_id=str(obj.id), form_url='')

    def force_onfido_routine(self, request: HttpRequest, obj: IndividualKYCSubmission) -> HttpResponseBadRequest:
        force_onfido_routine(obj)
        return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)

    def create_personal_agreement(self, request: HttpRequest, obj: IndividualKYCSubmission) -> HttpResponseRedirect:
        from jibrel.investment.models import PersonalAgreement
        model = PersonalAgreement
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add')
        return HttpResponseRedirect(f'{url}?user={obj.profile.user_id}')

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except BadTransitionError:
            messages.add_message(request, messages.ERROR, 'Transition restricted')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    reject.label = 'REJECT'
    approve.label = 'APPROVE'
    clone.label = 'CLONE'
    force_onfido_routine.label = 'FORCE ONFIDO ROUTINE'
    create_personal_agreement.label = 'Create personal agreement'

    change_actions = ('approve', 'reject', 'clone', 'force_onfido_routine', 'create_personal_agreement')

    @mark_safe
    def onfido_report(self, sub):
        if not sub.onfido_report:
            return
        return get_link_tag(sub.onfido_report.url, sub.onfido_report.name)

    def has_delete_permission(self, request, obj=None):
        return obj and obj.status == IndividualKYCSubmission.DRAFT

    def after_approve_hook(self, request, obj):
        kyc_approved.send(sender=self.model, instance=obj)

    def after_reject_hook(self, request, obj):
        kyc_rejected.send(sender=self.model, instance=obj)


@admin.register(OrganisationalKYCSubmission)
class OrganisationalKYCSubmissionAdmin(IndividualKYCSubmissionModelAdmin):
    form = OrganizationKYCSubmissionForm

    ordering = ('-created_at',)

    search_fields = ('profile__user__email', 'profile__user__uuid')

    list_display = (
        '__str__', 'status', 'onfido_result', 'created_at'
    )
    inlines = (
        BeneficiaryInline,
        DirectorInline,
        RegistrationAddressInline,
        PrincipalAddressInline
    )

    def get_fieldsets(self, request, obj=None):
        if self.__is_reject_form__(request, obj):
            return self.fieldsets_reject
        return (
            (None, {
                'fields': (
                    'account_type',
                    'status',
                )
            }),
            ('profile', {
                'fields': (
                    'user_link' if obj else 'profile',
                    ('first_name', 'middle_name', 'last_name',),
                    'birth_date',
                    'nationality',
                    'email',
                    'phone_number',
                )
            }),
            ('Current Residential Address', {
                'fields': (
                    'country',
                    'city',
                    'post_code',
                    ('street_address', 'apartment',),
                )
            }),
            ('Documentation', {
                'fields': (
                    'passport_number',
                    'passport_expiration_date',
                    'passport_document__file',
                    'proof_of_address_document__file'
                )
            }),
            ('onfido', {
                'fields': (
                    'onfido_applicant_id',
                    'onfido_check_id',
                    'onfido_result',
                    'onfido_report',
                ),
                'classes': ('collapse',),
            }),
            ('Company Info', {
                'fields': (
                    'company_name',
                    'trading_name',
                    'date_of_incorporation',
                    'place_of_incorporation',
                    'commercial_register__file',
                    'shareholder_register__file',
                    'articles_of_incorporation__file'
                )
            }),
            ('Submission', {
                'fields': (
                    'admin_note',
                    'reject_reason',
                )
            }),
            (_('Important dates'), {
                'fields': (
                    'created_at',
                    'transitioned_at'
                )
            }),
        )

    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        if self.__is_reject_form__(request, obj):
            return []
        return super().get_inline_formsets(request, formsets, inline_instances, obj)
