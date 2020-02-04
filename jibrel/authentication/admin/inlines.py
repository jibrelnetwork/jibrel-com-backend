from urllib import parse

from django import forms
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from nested_admin import nested

from django_banking.admin.helpers import (
    force_bool_value_display,
    force_empty_value_display
)
from jibrel.authentication.admin.formset import PhoneInlineFormset
from jibrel.authentication.models import (
    Phone,
    Profile
)
from jibrel.core.common.constants import BOOL_TO_STR


class PhoneInline(nested.NestedTabularInline):
    formset = PhoneInlineFormset
    model = Phone
    extra = 0
    fields = (
        'number',
        'status',
        'is_primary',
    )


class ProfileInline(nested.NestedStackedInline):
    model = Profile
    inlines = [PhoneInline]
    empty_value_display = '-'

    readonly_fields = (
        'current_phone',
        'current_phone_confirmed',
        'full_name',
        'passport_number',
        'passport_expiration_date',
        'nationality',
        'country',
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
        'nationality',
        'country',
        'full_name',
        'passport_number',
        'passport_expiration_date',
        'kyc_submissions',
    )

    formfield_overrides = {
        models.BooleanField: {
            'widget': forms.widgets.Select(choices=BOOL_TO_STR)
        },
    }

    @force_empty_value_display(empty_value_display)
    def nationality(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.details.nationality

    @force_empty_value_display(empty_value_display)
    def country(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.details.country

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
    def passport_number(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.details.passport_number

    @force_empty_value_display(empty_value_display)
    def passport_expiration_date(self, profile):
        kyc_submission = profile.last_kyc
        return kyc_submission and kyc_submission.details.passport_expiration_date

    @mark_safe
    @force_empty_value_display(empty_value_display)
    def kyc_submissions(self, profile):
        individual = profile.individualkycsubmission_set
        organisational = profile.organisationalkycsubmission_set

        def get_link(relation):
            qs = relation.all()
            model_meta = relation.model._meta
            if not qs:
                return

            url = reverse(f'admin:{model_meta.app_label}_{model_meta.model_name}_changelist')
            url += '?' + parse.urlencode({'q': str(profile.user.uuid)})
            return f'<a href={url}>{qs.count()} {model_meta.model_name}s</a>'

        return '<br/>'.join(filter(bool, (
            get_link(individual),
            get_link(organisational),
        )))

    current_phone.label = 'Current phone'
    current_phone_confirmed.label = 'Confirmed?'
    full_name.label = 'Full name'
    passport_number.label = 'Personal ID Number'
    passport_expiration_date.label = 'Personal ID Expiration Date'
    kyc_submissions.label = 'KYC Submissions'
