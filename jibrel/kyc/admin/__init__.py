from typing import Collection, Optional

from django.db import transaction
from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseRedirect
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions
from django_reverse_admin import ReverseModelAdmin

from jibrel.core.common.helpers import get_bad_request_response, get_link_tag
from jibrel.kyc.exceptions import BadTransitionError
from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)
from jibrel_admin.celery import (
    force_onfido_routine,
    send_kyc_approved_mail,
    send_kyc_rejected_mail
)

from .forms import (
    IndividualKYCSubmissionForm,
    OrganizationKYCSubmissionForm,
    RejectKYCSubmissionForm
)
from .inlines import (
    BeneficiaryInline,
    DirectorInline,
    OfficeAddressInline
)


@admin.register(IndividualKYCSubmission)
class IndividualKYCSubmissionModelAdmin(DjangoObjectActions, admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = IndividualKYCSubmissionForm

    ordering = ('-created_at',)

    search_fields = ('profile__user__email', 'profile__user__uuid')

    list_display = (
        '__str__', 'status', 'created_at'
    )

    fieldsets = (
        (None, {
            'fields': (
                'profile',
                'account_type',
                'status',
            )
        }),
        (None, {
            'fields': (
                ('first_name', 'middle_name', 'last_name',),
                'birth_date',
                'nationality',
                'email',
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
                'occupation_other',
                'income_source',
                'income_source_other'
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
        ('Agreements', {
            'fields': (
                'aml_agreed',
                'ubo_confirmed',
            ),
            'classes': ('collapse',),
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
                'created_at',
                'transitioned_at'
            )
        }),
    )

    radio_fields = {'status': admin.VERTICAL}

    def __is_reject_form__(self, request, obj):
        return obj and request.path == reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_actions', kwargs={
            'pk': obj.pk,
            'tool': 'reject'
        })

    def get_readonly_fields(self, request: HttpRequest, obj: BaseKYCSubmission = None) -> Collection[str]:
        if not obj or obj.status == BaseKYCSubmission.DRAFT:
            return (
                'status', 'onfido_result', 'onfido_report',
                'created_at',
                'transitioned_at'
            )
        elif self.__is_reject_form__(request, obj):
            return []

        all_fields = set(flatten_fieldsets(self.fieldsets))
        # TODO
        # https://code.djangoproject.com/ticket/29682
        return all_fields - {
            'admin_note',
            'reject_reason',
            'passport_document__file',
            'proof_of_address_document__file'
        }

    def get_fieldsets(self, request, obj=None):
        if self.__is_reject_form__(request, obj):
            return (
                (None, {
                    'fields': (
                        'reject_reason',
                    )
                }),
            )
        return super().get_fieldsets(request, obj)

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
            send_kyc_approved_mail(obj)
            self.message_user(request, 'Approved', level=messages.SUCCESS)
        except BadTransitionError:
            return get_bad_request_response('Transition restricted')

    def clone(self, request: HttpRequest, obj: BaseKYCSubmission) -> HttpResponseBadRequest:
        obj.clone()
        return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)

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
                send_kyc_rejected_mail(obj)
                self.message_user(request, 'Rejected')
            except BadTransitionError:
                messages.add_message(request, messages.ERROR, 'Transition restricted')
            return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)
        return self.changeform_view(request, object_id=str(obj.id), form_url='')

    def force_onfido_routine(self, request: HttpRequest, obj: IndividualKYCSubmission) -> HttpResponseBadRequest:
        force_onfido_routine(obj)
        return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)

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

    change_actions = ('approve', 'reject', 'clone', 'force_onfido_routine',)

    @mark_safe
    def onfido_report(self, sub):
        if not sub.onfido_report:
            return
        return get_link_tag(sub.onfido_report.url, sub.onfido_report.name)

    def has_delete_permission(self, request, obj=None):
        return obj and obj.status == IndividualKYCSubmission.DRAFT


@admin.register(OrganisationalKYCSubmission)
class OrganisationalKYCSubmissionAdmin(ReverseModelAdmin, IndividualKYCSubmissionModelAdmin):
    form = OrganizationKYCSubmissionForm

    ordering = ('-created_at',)

    search_fields = ('profile__user__email', 'profile__user__uuid')

    list_display = (
        '__str__', 'status', 'created_at'
    )
    inlines = (
        BeneficiaryInline,
        DirectorInline,
    )
    inline_type = 'stacked'
    inline_reverse = [
        {'field_name': 'company_address_registered', 'admin_class': OfficeAddressInline},
        {'field_name': 'company_address_principal', 'admin_class': OfficeAddressInline}
      ]

    fieldsets = (
        (None, {
            'fields': (
                'profile',
                'account_type',
                'status',
            )
        }),
        (None, {
            'fields': (
                ('first_name', 'middle_name', 'last_name',),
                'birth_date',
                'nationality',
                'email',
                'phone_number',
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
                'created_at',
                'transitioned_at'
            )
        }),
    )

