from operator import attrgetter

from django.contrib.admin import StackedInline, TabularInline

from django import forms
from .forms import (
    BeneficiaryForm,
    OfficeAddressForm
)

from ..models import (
    OfficeAddress,
    Beneficiary,
    Director
)


class DirectorInline(TabularInline):
    model = Director
    extra = 1

    def has_add_permission(self, request, obj=None):
        return not obj or obj.is_draft

    def has_delete_permission(self, request, obj=None):
        return not obj or obj.is_draft


class BeneficiaryInline(StackedInline, DirectorInline):
    model = Beneficiary
    form = BeneficiaryForm


class OfficeAddressInline(StackedInline):
    model = OfficeAddress
    form = OfficeAddressForm

