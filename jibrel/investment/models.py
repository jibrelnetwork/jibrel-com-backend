from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_banking.models import (
    Account,
    Operation
)
from django_banking.utils import generate_deposit_reference_code
from jibrel.campaigns.models import Offering

from ..core.common.rounding import rounded
from .enum import InvestmentApplicationStatus
from .managers import InvestmentApplicationManager
from .storages import personal_agreements_file_storage


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

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT, related_name='applications')
    offering = models.ForeignKey(Offering, on_delete=models.PROTECT, related_name='applications')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    deposit = models.ForeignKey(
        to='django_banking.Operation',
        on_delete=models.PROTECT,
        null=True,
        related_name='deposited_application',
    )
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
        return rounded(self.amount / self.offering.valuation, 6)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Investment {self.offering} - {self.user}'

    def add_payment(
        self,
        payment_account,
        user_account,
        user_bank_account,
        amount,
    ):
        """Creates payment for application
        This is temporary method which will help with further development of investment process

        For now, each application can have only one deposit which amount equals application's amount of funds.
        While user won't be able to withdraw funds, we can commit deposit operation, set HOLD status to application
        and don't create exchange operation.

        :param payment_account:
        :param user_account:
        :param user_bank_account:
        :param amount:
        :return:
        """

        operation = Operation.objects.create_deposit(
            payment_method_account=payment_account,
            user_account=user_account,
            amount=amount,
            references={
                'reference_code': self.deposit_reference_code,
                'user_bank_account_uuid': str(user_bank_account.uuid),
            },
        )
        try:
            operation.commit()
            self.deposit = operation
            self.status = InvestmentApplicationStatus.HOLD
            self.amount = amount
            self.save(update_fields=('deposit', 'status', 'amount'))
        except Exception as exc:
            operation.cancel()
            raise exc
        return operation



class PersonalAgreement(models.Model):
    offering = models.ForeignKey(Offering, on_delete=models.PROTECT)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)
    file = models.FileField(storage=personal_agreements_file_storage)
    is_agreed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['offering', 'user']
