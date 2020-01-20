from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_banking.models import Account
from django_banking.utils import generate_deposit_reference_code
from jibrel.campaigns.models import Offering

from .enum import InvestmentApplicationStatus
from .managers import InvestmentApplicationManager
from ..core.common.rounding import rounded


class InvestmentApplication(models.Model):
    objects = InvestmentApplicationManager()
    STATUS_CHOICES = (
        (InvestmentApplicationStatus.PENDING, _('Pending')),
        (InvestmentApplicationStatus.HOLD, _('Hold')),
        (InvestmentApplicationStatus.COMPLETED, _('Completed')),
        (InvestmentApplicationStatus.CANCELED, _('Canceled')),
        (InvestmentApplicationStatus.EXPIRED, _('Expired')),
        (InvestmentApplicationStatus.ERROR, _('Error')),
    )

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applications')
    offering = models.ForeignKey(Offering, on_delete=models.PROTECT, related_name='applications')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    deposit = models.ForeignKey(to='django_banking.Operation', on_delete=models.PROTECT, null=True)
    deposit_reference_code = models.CharField(max_length=100, default=generate_deposit_reference_code)

    amount = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2,
        verbose_name=_('amount')
    )

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES,
        default=InvestmentApplicationStatus.PENDING
    )

    is_agreed_risks = models.BooleanField(default=False)
    is_agreed_subscription = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @cached_property
    def asset(self):
        return self.account.asset

    @cached_property
    def ownership(self):
        return rounded(100 * self.amount / self.offering.valuation, 6)
