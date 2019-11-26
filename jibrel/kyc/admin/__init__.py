from typing import Collection, Optional

from django.contrib import admin, messages
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseRedirect
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from jibrel.core.common.helpers import get_bad_request_response, get_link_tag
from jibrel.kyc.exceptions import BadTransitionError
from jibrel.kyc.models import BasicKYCSubmission
from jibrel_admin.celery import (
    force_onfido_routine,
    send_kyc_approved_mail,
    send_kyc_rejected_mail
)

from .forms import BasicKYCSubmissionForm, RejectKYCSubmissionForm


@admin.register(BasicKYCSubmission)
class BasicKYCSubmissionModelAdmin(DjangoObjectActions, admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = BasicKYCSubmissionForm

    ordering = ('-created_at',)

    search_fields = ('profile__user__email', 'profile__user__uuid')

    list_display = (
        '__str__', 'status', 'created_at'
    )

    fields = (
        'profile', 'citizenship', 'residency', 'first_name', 'middle_name',
        'last_name', 'birth_date', 'birth_date_hijri', 'is_birth_date_hijri',
        'personal_id_type', 'personal_id_number', 'personal_id_doe', 'personal_id_doe_hijri',
        'is_personal_id_doe_hijri', 'personal_id_document_front_file', 'personal_id_document_back_file',
        'residency_visa_number', 'residency_visa_doe', 'residency_visa_doe_hijri',
        'is_residency_visa_doe_hijri', 'residency_visa_document_file', 'is_agreed_aml_policy',
        'is_confirmed_ubo', 'status', 'onfido_result', 'onfido_report', 'admin_note', 'reject_reason',
    )

    radio_fields = {'status': admin.VERTICAL}

    def __is_reject_form__(self, request, obj):
        return obj and request.path == reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_actions', kwargs={
            'pk': obj.pk,
            'tool': 'reject'
        })

    def get_readonly_fields(self, request: HttpRequest, obj: BasicKYCSubmission = None) -> Collection[str]:
        if not (obj and obj.status != BasicKYCSubmission.DRAFT):
            return (
                'status', 'onfido_result', 'onfido_report',
            )
        elif self.__is_reject_form__(request, obj):
            return ()
        return (
            'profile', 'citizenship', 'residency', 'first_name', 'middle_name', 'last_name', 'birth_date',
            'birth_date_hijri', 'is_birth_date_hijri', 'personal_id_type', 'personal_id_number',
            'personal_id_doe', 'personal_id_document_front_file', 'personal_id_doe_hijri',
            'is_personal_id_doe_hijri', 'personal_id_document_back_file', 'residency_visa_number',
            'residency_visa_doe', 'residency_visa_doe_hijri', 'is_residency_visa_doe_hijri',
            'residency_visa_document_file', 'is_agreed_aml_policy', 'is_confirmed_ubo',
            'created_at', 'transitioned_at', 'status', 'onfido_result', 'onfido_report', 'reject_reason'
        )

    def get_fields(self, request, obj=None):
        if self.__is_reject_form__(request, obj):
            return 'reject_reason',
        return super().get_fields(request, obj)

    def get_form(self, request, obj=None, change=False, **kwargs):
        defaults = {}
        if self.__is_reject_form__(request, obj):
            defaults['form'] = RejectKYCSubmissionForm
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def approve(self, request: HttpRequest, obj: BasicKYCSubmission) -> Optional[HttpResponseBadRequest]:
        if obj.is_approved():
            self.message_user(request, 'Approved already', level=messages.SUCCESS)
            return
        try:
            obj.approve()
            send_kyc_approved_mail(obj)
            self.message_user(request, 'Approved', level=messages.SUCCESS)
        except BadTransitionError:
            return get_bad_request_response('Transition restricted')

    def clone(self, request: HttpRequest, obj: BasicKYCSubmission) -> HttpResponseBadRequest:
        obj.clone()
        return redirect(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', object_id=obj.pk)

    def reject(self, request: HttpRequest, obj: BasicKYCSubmission):
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

    def force_onfido_routine(self, request: HttpRequest, obj: BasicKYCSubmission) -> HttpResponseBadRequest:
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

    def personal_id_document_front_file(self, sub):
        file = sub.personal_id_document_front.file
        return mark_safe(
            get_link_tag(file.url, file.name)
        )

    def personal_id_document_back_file(self, sub):
        file = sub.personal_id_document_back.file
        return mark_safe(
            get_link_tag(file.url, file.name)
        )

    def residency_visa_document_file(self, sub):
        file = sub.residency_visa_document.file
        return mark_safe(
            get_link_tag(file.url, file.name)
        )

    def onfido_report(self, sub):
        if not sub.onfido_report:
            return
        return mark_safe(
            get_link_tag(sub.onfido_report.url, sub.onfido_report.name)
        )

    def has_delete_permission(self, request, obj=None):
        return obj and obj.status == BasicKYCSubmission.DRAFT
