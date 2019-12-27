from uuid import uuid4

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from kombu.utils import cached_property

from django_banking.exceptions import AccountBalanceException

from ...core.db.fields import DecimalField
from ...settings import USER_MODEL
from .. import Asset
from ..transactions.enum import OperationStatus
from .enum import AccountType
from .managers import (
    BaseUserAccountManager,
    UserAccountManager
)
from .queryset import AccountQuerySet


class Account(models.Model):

    """Bookkeeping account object.
    """

    TYPE_CHOICES = (
        (AccountType.TYPE_NORMAL, 'Normal'),
        (AccountType.TYPE_ACTIVE, 'Active'),
        (AccountType.TYPE_PASSIVE, 'Passive'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    #: asset/currency counted by this account
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, db_index=True)

    #: account type
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    #: limit allowed transactions to debit only
    strict = models.BooleanField()

    #: can be used to backup references in case they were lost in the main system
    references = JSONField(default=dict, db_index=True)

    objects = AccountQuerySet.as_manager()

    def is_valid(self, include_new=True):
        """Validate account balance against visible operations, including new.
        """
        if self.type == AccountType.TYPE_NORMAL:
            return True

        balance = self.calculate_balance(include_new)

        if self.type == AccountType.TYPE_ACTIVE and balance < 0:
            raise AccountBalanceException(
                self, "Balance of active account is less than 0"
            )
        if self.type == AccountType.TYPE_PASSIVE and balance > 0:
            raise AccountBalanceException(
                self, "Balance of passive account is greater than 0"
            )

        return True

    def calculate_balance(self, include_new=True):
        from django_banking.models import Transaction
        balance_qs = Transaction.objects.filter(account=self)

        exclude_op_statuses = [
            OperationStatus.DELETED,
            OperationStatus.CANCELLED
        ]

        if include_new is False:
            exclude_op_statuses.append(OperationStatus.NEW)

        balance_qs = balance_qs.exclude(
            operation__status__in=exclude_op_statuses)

        return balance_qs.aggregate(
            balance=Coalesce(
                Sum('amount'),
                0,
                output_field=DecimalField()
            )
        )['balance']

    def __str__(self) -> str:
        return f'Account(asset={self.asset.symbol})'

    @cached_property
    def is_active(self):
        return self.type == AccountType.TYPE_PASSIVE


class AbstractUserAccount(models.Model):
    """User asset bookkeeping account.

    Customer may have single account per asset.
    """
    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    objects = UserAccountManager()

    class Meta:
        abstract = True


class UserAccount(AbstractUserAccount):
    """User to bookkeeping account relation for API.
    """


class UserFeeAccount(AbstractUserAccount):
    """Fee account for user"""

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=AccountType.TYPE_ACTIVE, strict=True))


class UserExchangeAccount(AbstractUserAccount):
    """Account for exchange operations for user"""

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=AccountType.TYPE_NORMAL, strict=False))


class UserRoundingAccount(AbstractUserAccount):
    """Account for rounding remains in operations for user"""

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=AccountType.TYPE_NORMAL, strict=False))
