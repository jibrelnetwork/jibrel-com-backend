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
    )

    offering = models.ForeignKey(Offering, on_delete=models.PROTECT, related_name='applications')
    account = models.ForeignKey(UserAccount, on_delete=models.PROTECT)
    shares = models.PositiveIntegerField()

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES,
        default=InvestmentApplicationStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
