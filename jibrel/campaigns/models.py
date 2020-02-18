import uuid
from decimal import Decimal

from django.conf import settings
from django.db import (
    ProgrammingError,
    models
)
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_banking.models import Asset

from ..core.common.helpers import (
    default_value_for_new_object,
    get_from_qs
)
from ..core.common.rounding import rounded
from .enum import (
    OfferingStatus,
    RoundName,
    SecurityType
)
from .managers import OfferingManager


class Company(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100, verbose_name=_('Title'))
    slug = models.CharField(max_length=64, unique=True,
                            help_text=_('Should be identical to the CMS slug'))

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')

    def __str__(self):
        return self.name


class Security(models.Model):
    TYPE_DEFAULT = SecurityType.COMMON_SHARES
    TYPE_CHOICES = (
        (SecurityType.COMMON_SHARES, _('Common shares')),
        (SecurityType.CONVERTIBLE_DEBT, _('Convertible bond')),
        (SecurityType.PREFERRED_SHARES, _('Preferred Shares')),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = models.CharField(
        max_length=32, choices=TYPE_CHOICES,
        verbose_name=_('type'),
        help_text=_('Once created, type cannot be changed anymore.'),
        default=TYPE_DEFAULT
    )
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='securities')
    asset = models.OneToOneField(Asset, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.company.name}, {self.type}'

    class Meta:
        verbose_name = _('Security')
        verbose_name_plural = _('Securities')


class Offering(models.Model):
    objects = OfferingManager()
    ROUND_CHOICES = (
        (RoundName.ANGEL, 'Angel'),
        (RoundName.SEED, 'Seed'),
        (RoundName.A, 'A'),
        (RoundName.B, 'B'),
        (RoundName.C, 'C'),
        (RoundName.D, 'D'),
    )

    STATUS_CHOICES = (
        (OfferingStatus.DRAFT, _('Draft')),
        (OfferingStatus.WAITLIST, _('Wait list')),
        (OfferingStatus.ACTIVE, _('Active')),
        (OfferingStatus.CLEARING, _('Clearing')),
        (OfferingStatus.COMPLETED, _('Completed')),
        (OfferingStatus.CANCELED, _('Canceled')),
    )
    STATUS_PIPELINE = {
        OfferingStatus.DRAFT: [OfferingStatus.WAITLIST],
        OfferingStatus.WAITLIST: [OfferingStatus.ACTIVE],
        OfferingStatus.ACTIVE: [OfferingStatus.WAITLIST, OfferingStatus.CLEARING],
        OfferingStatus.CLEARING: [OfferingStatus.ACTIVE, OfferingStatus.CANCELED],
        OfferingStatus.COMPLETED: [],
        OfferingStatus.CANCELED: []
    }

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    security = models.ForeignKey(Security, on_delete=models.PROTECT)

    limit_min_amount = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2,
        verbose_name=_('min investment amount per user'),
        default=Decimal(1)
    )
    limit_max_amount = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2,
        verbose_name=_('max investment amount per user'),
        blank=True, null=True
    )

    date_start = models.DateTimeField(verbose_name=_('campaign starts time'))
    date_end = models.DateTimeField(verbose_name=_('deadline'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    valuation = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2, verbose_name=_('valuation'),
        help_text=_('Valuation must be same across all campaign rounds.')
    )
    goal = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2, verbose_name=_('Round size'),
        help_text=_('Cannot be grater then valuation')
    )
    round = models.CharField(
        max_length=32, choices=ROUND_CHOICES,
        verbose_name=_('Round name')
    )

    shares = models.PositiveIntegerField(
        verbose_name=_('Total number of shares'),
        blank=True,
        null=True
    )
    price = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=2,
        verbose_name=_('Single share price'),
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES,
        default=OfferingStatus.DRAFT
    )

    class Meta:
        verbose_name = _('Fundraising offering')
        verbose_name_plural = _('Fundraising offerings')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.security.company.name} ({self.round})'

    @cached_property
    def is_active(self):
        """
        Round is active after first application applied
        """
        return self.applications.exists()

    @cached_property
    def limit_allowed_amount(self):
        """
        Actually is should be at further releases
        min(
            self.limit_max_amount or self.goal,
            self.goal - (
                self.hold_money_sum + self.completed_money_sum
            )
        )
        """
        return self.limit_max_amount or self.goal

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def total_money_sum(self):
        raise ProgrammingError('Queryset must be called with with_money_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def pending_money_sum(self):
        raise ProgrammingError('Queryset must be called with with_money_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def hold_money_sum(self):
        raise ProgrammingError('Queryset must be called with with_money_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def completed_money_sum(self):
        raise ProgrammingError('Queryset must be called with with_money_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def canceled_money_sum(self):
        raise ProgrammingError('Queryset must be called with with_money_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def total_applications_count(self):
        raise ProgrammingError('Queryset must be called with with_application_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def pending_applications_count(self):
        raise ProgrammingError('Queryset must be called with with_application_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def hold_applications_count(self):
        raise ProgrammingError('Queryset must be called with with_application_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def completed_applications_count(self):
        raise ProgrammingError('Queryset must be called with with_application_statistics() method')

    @cached_property
    @default_value_for_new_object(0)
    @get_from_qs
    def canceled_applications_count(self):
        raise ProgrammingError('Queryset must be called with with_application_statistics() method')

    @cached_property
    def equity(self):
        return rounded(self.goal / self.valuation, 6)
