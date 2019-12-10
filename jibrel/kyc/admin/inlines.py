from django.contrib.admin import StackedInline, TabularInline

from ..models import (
    OfficeAddress,
    Beneficiary,
    Director
)


class BeneficiaryInline(StackedInline):
    model = Beneficiary
    extra = 1


class DirectorInline(TabularInline):
    model = Director
    extra = 1


class OfficeAddressInline(StackedInline):
    model = OfficeAddress
