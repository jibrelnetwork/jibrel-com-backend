from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_banking.models import UserAccount
from jibrel.campaigns.models import Offering

from .enum import InvestmentApplicationStatus


class InvestmentApplication(models.Model):
    STATUS_CHOICES = (
        (InvestmentApplicationStatus.PENDING, _('Pending')),
        (InvestmentApplicationStatus.HOLD, _('Hold')),
        (InvestmentApplicationStatus.COMPLETED, _('Completed')),
        (InvestmentApplicationStatus.CANCELED, _('Canceled')),
        (InvestmentApplicationStatus.EXPIRED, _('Expired')),
        (InvestmentApplicationStatus.ERROR, _('Error')),
    )

    offering = models.ForeignKey(Offering, on_delete=models.PROTECT, related_name='applications')
    account = models.ForeignKey(UserAccount, on_delete=models.PROTECT)

    amount = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2,
        verbose_name=_('amount')
    )
    references = JSONField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES,
        default=InvestmentApplicationStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
