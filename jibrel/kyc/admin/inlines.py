from operator import attrgetter

from django import forms
from django.contrib.admin import (
    StackedInline,
    TabularInline
)

from ..models import (
    Beneficiary,
    Director,
    OfficeAddress
)
from .forms import (
    BeneficiaryForm,
    OfficeAddressForm
)


class KYCInlineMixin:
    def get_extra(self, request, obj=None, **kwargs):
        if obj is None:
            return 1
        return 0

    def has_add_permission(self, request, obj=None):
        return not obj or obj.is_draft

    def has_delete_permission(self, request, obj=None):
        return not obj or obj.is_draft

    def get_readonly_fields(self, request, obj=None):
        if not obj or obj.is_draft:
            return []

        fields = forms.ALL_FIELDS
        if hasattr(self.form, 'Meta'):
            fields = getattr(self.form.Meta, 'fields', forms.ALL_FIELDS)
        if fields == forms.ALL_FIELDS:
            fields = set(map(attrgetter('name'), self.model._meta.get_fields()))

        try:
            exclude = set(getattr(self.form.Meta, 'exclude', []))
        except AttributeError:
            exclude = set()
        return fields - exclude


class DirectorInline(KYCInlineMixin, TabularInline):
    model = Director


class BeneficiaryInline(KYCInlineMixin, StackedInline):
    model = Beneficiary
    form = BeneficiaryForm

    def get_readonly_fields(self, request, obj=None):
        return (
            'onfido_applicant_id',
            'onfido_check_id',
            'onfido_result',
            'onfido_report',
        )


class RegistrationAddressInline(KYCInlineMixin, StackedInline):
    model = OfficeAddress
    form = OfficeAddressForm
    fk_name = 'kyc_registered_here'
    min_num = 1
    verbose_name = "Registration Address"
    verbose_name_plural = verbose_name


class PrincipalAddressInline(RegistrationAddressInline):
    fk_name = 'kyc_principal_here'
    min_num = 0
    verbose_name = "Principal Address"
    verbose_name_plural = verbose_name
