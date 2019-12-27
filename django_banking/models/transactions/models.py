from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Sum
from django.utils.functional import cached_property

from django_banking import module_name
from django_banking.core.db.fields import DecimalField
from django_banking.models import Asset, Account
from django_banking.user import User
from .enum import OperationStatus, OperationType
from .exceptions import AccountStrictnessException, OperationBalanceException
from .managers import OperationManager
from .queryset import PaymentOperationQuerySet
from ..accounts.enum import AccountType
from ...settings import CRYPTO_BACKEND_ENABLED, CARD_BACKEND_ENABLED, WIRE_TRANSFER_BACKEND_ENABLED
from ...storages import operation_upload_storage


class Operation(models.Model):

    """Bookkeeping system Operation object.
    """
    STATUS_CHOICES = (
        (OperationStatus.NEW, 'New'),
        (OperationStatus.HOLD, 'On hold'),
        (OperationStatus.COMMITTED, 'Committed'),
        (OperationStatus.CANCELLED, 'Cancelled'),
        (OperationStatus.DELETED, 'Deleted'),
    )

    TYPE_CHOICES = (
        (OperationType.DEPOSIT, 'Deposit'),
        (OperationType.WITHDRAWAL, 'Withdrawal'),
        (OperationType.BUY, 'Buy'),
        (OperationType.SELL, 'Sell'),
        (OperationType.CORRECTION, 'Correction')
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OperationStatus.NEW, db_index=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_index=True)

    description = models.TextField(default='')
    references = JSONField(default=dict, db_index=True)

    metadata = JSONField(default=dict, db_index=True)

    objects = OperationManager()

    def is_valid(self, include_new=True):
        """Check if current operation is valid and can be safely held.

        Check total transactions balance by each affected asset/currency.
        """
        for asset, balance in self.get_per_asset_balances():
            if balance != 0:
                raise OperationBalanceException(self, asset)

        qs = self.transactions.all()

        for tx in qs.select_related('account'):
            tx.is_valid()
            tx.account.is_valid(include_new=include_new)

        return True

    def hold(self):
        """Validate and hold operation if valid.
        """
        self.is_valid()
        self.status = OperationStatus.HOLD
        self.save(update_fields=('status',))

    def commit(self):
        """Commit operation and all containing transactions.
        """
        assert self.status == OperationStatus.HOLD
        self.is_valid(include_new=False)
        self.status = OperationStatus.COMMITTED
        self.save(update_fields=('status',))

    def cancel(self):
        """Cancels operation and all containing transactions.
        """
        self.status = OperationStatus.CANCELLED
        self.save(update_fields=('status',))

    def reject(self, reason):
        self.status = OperationStatus.DELETED
        self.references['reject_reason'] = reason
        self.save(update_fields=('status', 'references'))

    @property
    def is_committed(self):
        return self.status == OperationStatus.COMMITTED

    @property
    def is_cancelled(self):
        return self.status == OperationStatus.CANCELLED

    def get_per_asset_balances(self):
        balance_annotation = Sum(
            'account__transaction__amount',
        )
        qs = Asset.objects.filter(account__transaction__operation=self) \
            .annotate(balance=balance_annotation)

        for asset in qs:
            yield asset, asset.balance or 0

    @cached_property
    def user(self):
        return User.objects.filter(
            useraccount__account__transaction__operation_id=self.pk
        ).first()

    @cached_property
    def bank_account(self):
        if not WIRE_TRANSFER_BACKEND_ENABLED:
            return None
        from ...contrib.wire_transfer.models import UserBankAccount
        try:
            user_bank_account_id = self.references.get('user_bank_account_uuid')
            return UserBankAccount.objects.filter(pk=user_bank_account_id).first()
        except ObjectDoesNotExist:
            return None

    @cached_property
    def card_account(self):
        if not CARD_BACKEND_ENABLED:
            return None
        from ...contrib.card.models import UserCardAccount
        try:
            return UserCardAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None

    @cached_property
    def cryptocurrency_address(self):
        if not CRYPTO_BACKEND_ENABLED:
            return None
        from ...contrib.crypto.models import UserCryptoAccount
        try:
            return UserCryptoAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None

    @cached_property
    def deposit_cryptocurrency_address(self):
        if not CRYPTO_BACKEND_ENABLED:
            return None
        from ...contrib.crypto.models import UserCryptoDepositAccount
        try:
            return UserCryptoDepositAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None


class Transaction(models.Model):

    """Transaction object.
    """

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation = models.ForeignKey(Operation, on_delete=models.CASCADE,
                                  related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    amount = DecimalField()

    #: can be used to backup references in case they were lost in the main system
    references = JSONField(default=dict, db_index=True)

    def is_valid(self):
        if self.account.strict:
            if self.account.type == AccountType.TYPE_ACTIVE and self.amount < 0:
                raise AccountStrictnessException(
                    self,
                    "Negative amount transaction on strictly active account."
                )
            if self.account.type == AccountType.TYPE_PASSIVE and self.amount > 0:
                raise AccountStrictnessException(
                    self,
                    "Positive amount transaction on strictly passive account."
                )
        return True


class PaymentOperation(Operation):
    objects = PaymentOperationQuerySet.as_manager()

    class Meta:
        proxy = True


class OperationConfirmationDocument(models.Model):
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT)
    file = models.FileField(storage=operation_upload_storage)
    created_at = models.DateTimeField(auto_now_add=True)
