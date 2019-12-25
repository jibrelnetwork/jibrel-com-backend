from urllib import parse

from django import forms
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from nested_admin import nested

from jibrel.authentication.models import (
    Phone,
    Profile
)
from jibrel.core.common.constants import BOOL_TO_STR
from django_banking.admin.helpers import (
    force_bool_value_display,
    force_empty_value_display
)


class PhoneInline(nested.NestedTabularInline):
    model = Phone
    extra = 0
    fields = (
        'number',
        'status',
    )


class ProfileInline(nested.NestedStackedInline):
    model = Profile
    inlines = [PhoneInline]
    empty_value_display = '-'

    readonly_fields = (
        'current_phone',
        'current_phone_confirmed',
        'full_name',
        'personal_id_number',
        'personal_id_doe',
        'citizenship',
        'residency',
        'kyc_submissions',
        'kyc_status',
    )
    fields = (
        'username',
        'current_phone',
        'current_phone_confirmed',
        'is_agreed_documents',
        'language',
        'kyc_status',
        'citizenship',
        'residency',
        'full_name',
        'personal_id_number',
        'personal_id_doe',
        'kyc_submissions',
    )

    formfield_overrides = {
        models.BooleanField: {
            'widget': forms.widgets.Select(choices=BOOL_TO_STR)
        },
    }

    @force_empty_value_display(empty_value_display)
    def citizenship(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.citizenship

    @force_empty_value_display(empty_value_display)
    def residency(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.residency

    @force_empty_value_display(empty_value_display)
    def current_phone(self, profile):
        phone = profile.phone
        return phone and phone.number

    @force_bool_value_display('Yes', 'No')
    def current_phone_confirmed(self, profile: Profile):
        return bool(profile.phone and profile.phone.is_confirmed)

    @force_empty_value_display(empty_value_display)
    def full_name(self, profile: Profile):
        return profile.username

    @force_empty_value_display(empty_value_display)
    def personal_id_number(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.personal_id_number

    @force_empty_value_display(empty_value_display)
    def personal_id_doe(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.personal_id_doe

    @force_empty_value_display(empty_value_display)
    def residency_visa_number(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.residency_visa_number

    @force_empty_value_display(empty_value_display)
    def residency_visa_doe(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.residency_visa_doe

    @force_empty_value_display(empty_value_display)
    def kyc_submissions(self, profile):
        model_meta = profile.basic_submissions.model._meta
        url = reverse(f'admin:{model_meta.app_label}_{model_meta.model_name}_changelist')
        url += '?' + parse.urlencode({'q': str(profile.user.uuid)})
        return mark_safe(
            f'<a href={url}>{profile.basic_submissions.count()} items</a>'
        )

    current_phone.label = 'Current phone'
    current_phone_confirmed.label = 'Confirmed?'
    full_name.label = 'Full name'
    personal_id_number.label = 'Personal ID Number'
    personal_id_doe.label = 'Personal ID Expiration Date'
    residency_visa_number.label = 'Residency Visa Number'
    residency_visa_doe.label = 'Residency Visa Expiration Date'
    kyc_submissions.label = 'KYC Submissions'
