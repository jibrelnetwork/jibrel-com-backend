import decimal
from typing import Dict
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.db.models import Q, Sum
from django.db.models import Value as V
from django.db.models.functions import Coalesce

from .exceptions import (
    AccountBalanceException,
    AccountStrictnessException,
    OperationBalanceException
)


class DecimalField(models.DecimalField):

    """Decimal field with default account precision.

    Use `ACCOUNTING_MAX_DIGITS` and `ACCOUNTING_DECIMAL_PLACES` settings as defaults
    for `max_digits` and `decimal_places` kwargs.
    """

    def __init__(self, **kwargs):
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = settings.ACCOUNTING_MAX_DIGITS
        if 'decimal_places' not in kwargs:
            kwargs['decimal_places'] = settings.ACCOUNTING_DECIMAL_PLACES
        super().__init__(**kwargs)


class AssetManager(models.Manager):

    def for_customer(self, user) -> models.QuerySet:
        user_country = user.get_residency_country_code()
        return self.filter(
            Q(type=Asset.CRYPTO) | Q(type=Asset.FIAT, country=user_country)
        )

    def main_fiat_for_customer(self, user) -> 'Asset':
        user_country = user.get_residency_country_code()
        return self.filter(
            type=Asset.FIAT, country=user_country
        ).first()


class Asset(models.Model):

    """Countable Asset object.

    Used as a reference in other models and outside app.
    """

    FIAT = 'fiat'
    CRYPTO = 'crypto'

    TYPE_CHOICES = (
        (FIAT, 'Fiat'),
        (CRYPTO, 'Cryptocurrency'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    type = models.CharField(choices=TYPE_CHOICES, max_length=10)

    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    country = models.CharField(max_length=2, null=True)

    decimals = models.SmallIntegerField(default=6)

    objects = AssetManager()

    def __str__(self):
        if self.type == self.CRYPTO:
            return f'{self.symbol}'
        return f'{self.symbol} ({self.country})'


class AccountQuerySet(models.QuerySet):

    def with_balances(self):
        return self.annotate(
           balance=Coalesce(
               Sum(
                   'transaction__amount',
                   filter=Q(
                       transaction__operation__type=Operation.DEPOSIT,
                       transaction__operation__status=Operation.COMMITTED,
                   ) | Q(
                       transaction__operation__type=Operation.WITHDRAWAL,
                       transaction__operation__status__in=[Operation.HOLD, Operation.COMMITTED],
                   ) | Q(
                       transaction__operation__type=Operation.BUY,
                       transaction__account__asset__type=Asset.CRYPTO,
                       transaction__operation__status=Operation.COMMITTED,
                   ) | Q(
                       transaction__operation__type=Operation.BUY,
                       transaction__account__asset__type=Asset.FIAT,
                       transaction__operation__status__in=[Operation.HOLD, Operation.COMMITTED],
                   ) | Q(
                       transaction__operation__type=Operation.SELL,
                       asset__type=Asset.FIAT,
                       transaction__operation__status=Operation.COMMITTED,
                   ) | Q(
                       transaction__operation__type=Operation.SELL,
                       asset__type=Asset.CRYPTO,
                       transaction__operation__status__in=[Operation.HOLD, Operation.COMMITTED],
                   )
               ),
               V(0)
           )
        )


class Account(models.Model):

    """Bookkeeping account object.
    """

    TYPE_ACTIVE = 'active'
    TYPE_PASSIVE = 'passive'
    TYPE_NORMAL = 'normal'

    TYPE_CHOICES = (
        (TYPE_NORMAL, 'Normal'),
        (TYPE_ACTIVE, 'Active'),
        (TYPE_PASSIVE, 'Passive'),
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
        if self.type == self.TYPE_NORMAL:
            return True

        balance = self.calculate_balance(include_new)

        if self.type == self.TYPE_ACTIVE and balance < 0:
            raise AccountBalanceException(
                self, "Balance of active account is less than 0"
            )
        if self.type == self.TYPE_PASSIVE and balance > 0:
            raise AccountBalanceException(
                self, "Balance of passive account is greater than 0"
            )

        return True

    def calculate_balance(self, include_new=True):
        balance_qs = Transaction.objects.filter(account=self)

        exclude_op_statuses = [
            Operation.DELETED,
            Operation.CANCELLED
        ]

        if include_new is False:
            exclude_op_statuses.append(Operation.NEW)

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


class OperationManager(models.Manager):

    """Operations manager.

    Some of the methods requires to run only outside of db transaction to
    overcome transaction isolation.
    """

    def create_deposit(self,
                       payment_method_account: Account,
                       user_account: Account,
                       amount: decimal.Decimal,
                       fee_account: Account = None,
                       fee_amount: decimal.Decimal = None,
                       rounding_account: Account = None,
                       rounding_amount: decimal.Decimal = None,
                       references: Dict = None,
                       hold: bool = True,
                       metadata: Dict = None) -> 'Operation':
        """Create deposit operation request.

        :param payment_method_account: payment method account to debit amount
        :param user_account: bookkeeping account to credit specified amount
        :param amount: amount of assets to deposit
        :param fee_account: account to debit fee from user account
        :param fee_amount: amount of fee
        :param rounding_account: account to capture rounding remains from payment method account
        :param rounding_amount: amount of rounding remain
        :param references: dict with additional data for operation
        :param hold: operation will be automatically held
        :param metadata: dict of additional data for user
        """
        assert amount > 0, "Deposit amount must be greater than 0"

        with transaction.atomic():
            operation = self.create(
                type=Operation.DEPOSIT,
                references=references or {},
                metadata=metadata or {},
            )

            operation.transactions.create(account=payment_method_account, amount=-amount)
            operation.transactions.create(account=user_account, amount=amount)

            if fee_account and fee_amount:
                operation.transactions.create(account=user_account, amount=-fee_amount)
                operation.transactions.create(account=fee_account, amount=fee_amount)

            if rounding_amount and rounding_account:
                operation.transactions.create(account=payment_method_account, amount=rounding_amount)
                operation.transactions.create(account=rounding_account, amount=-rounding_amount)

        return self._validate_hold_or_delete(operation, hold)

    def create_withdrawal(self,
                          user_account: Account,
                          payment_method_account: Account,
                          amount: decimal.Decimal,
                          fee_account: Account = None,
                          fee_amount: decimal.Decimal = None,
                          rounding_account: Account = None,
                          rounding_amount: decimal.Decimal = None,
                          references: Dict = None,
                          hold: bool = True,
                          metadata: Dict = None) -> 'Operation':
        """Create withdrawal operation request and hold funds.

        :param user_account: user account to debit
        :param payment_method_account: payment method account to credit
        :param amount: amount of assets to withdraw
        :param fee_account: account to debit fee from user account
        :param fee_amount: amount of fee
        :param rounding_account: account to capture rounding remains from payment method account
        :param rounding_amount: amount of rounding remain
        :param references: dict with additional data for operation
        :param hold: operation will be automatically held
        :param metadata: dict of additional data for user
        """
        assert amount > 0, "Withdrawal amount must be greater than 0"

        with transaction.atomic():
            operation = self.create(
                type=Operation.WITHDRAWAL,
                references=references or {},
                metadata=metadata or {},
            )

            operation.transactions.create(account=user_account, amount=-amount)
            operation.transactions.create(account=payment_method_account, amount=amount)

            if fee_amount and fee_account:
                operation.transactions.create(account=user_account, amount=-fee_amount)
                operation.transactions.create(account=fee_account, amount=fee_amount)

            if rounding_amount and rounding_account:
                operation.transactions.create(account=payment_method_account, amount=rounding_amount)
                operation.transactions.create(account=rounding_account, amount=-rounding_amount)

        return self._validate_hold_or_delete(operation, hold)

    def create_exchange(
        self,
        base_account: Account,
        base_exchange_account: Account,
        base_amount: decimal.Decimal,
        quote_account: Account,
        quote_exchange_account: Account,
        quote_amount: decimal.Decimal,
        fee_account: Account,
        fee_amount: decimal.Decimal,
        base_rounding_account: Account = None,
        base_rounding_amount: decimal.Decimal = None,
        quote_rounding_account: Account = None,
        quote_rounding_amount: decimal.Decimal = None,
        references: Dict = None,
        hold: bool = True,
        metadata: Dict = None,
    ) -> 'Operation':
        assert base_amount * quote_amount < 0, 'Exchange operation must decrease one account and increase another'
        assert fee_amount >= 0, 'Fee can\'t be negative'
        with transaction.atomic():
            operation = self.create(
                type=Operation.BUY if base_amount > 0 else Operation.SELL,
                references=references or {},
                metadata=metadata or {},
            )

            operation.transactions.create(account=base_account, amount=base_amount)
            operation.transactions.create(account=base_exchange_account, amount=-base_amount)
            operation.transactions.create(account=quote_account, amount=quote_amount)
            operation.transactions.create(account=quote_exchange_account, amount=-quote_amount)
            operation.transactions.create(account=quote_account, amount=-fee_amount)
            operation.transactions.create(account=fee_account, amount=fee_amount)
            if base_rounding_amount and base_rounding_account:
                operation.transactions.create(account=base_exchange_account, amount=base_rounding_amount)
                operation.transactions.create(account=base_rounding_account, amount=-base_rounding_amount)
            if quote_rounding_amount and quote_rounding_account:
                operation.transactions.create(account=quote_exchange_account, amount=quote_rounding_amount)
                operation.transactions.create(account=quote_rounding_account, amount=-quote_rounding_amount)

        return self._validate_hold_or_delete(operation, hold)

    @staticmethod
    def _validate_hold_or_delete(operation, hold=True):
        try:
            operation.is_valid()
        except:
            operation.delete()
            raise

        if hold:
            try:
                operation.hold()

                return operation
            finally:
                if operation.status != Operation.HOLD:
                    operation.delete()
        return operation


class Operation(models.Model):

    """Bookkeeping system Operation object.
    """

    NEW = 'new'
    HOLD = 'hold'
    COMMITTED = 'committed'
    CANCELLED = 'cancelled'
    DELETED = 'deleted'

    STATUS_CHOICES = (
        (NEW, 'New'),
        (HOLD, 'On hold'),
        (COMMITTED, 'Committed'),
        (CANCELLED, 'Cancelled'),
        (DELETED, 'Deleted'),
    )

    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    BUY = 'buy'
    SELL = 'sell'
    CORRECTION = 'correction'

    TYPE_CHOICES = (
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (BUY, 'Buy'),
        (SELL, 'Sell'),
        (CORRECTION, 'Correction')
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=NEW, db_index=True)
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
        self.status = Operation.HOLD
        self.save(update_fields=('status',))

    def commit(self):
        """Commit operation and all containing transactions.
        """
        assert self.status == self.HOLD
        self.is_valid(include_new=False)
        self.status = Operation.COMMITTED
        self.save(update_fields=('status',))

    def cancel(self):
        """Cancels operation and all containing transactions.
        """
        self.status = self.CANCELLED
        self.save(update_fields=('status',))

    def reject(self, reason):
        self.status = Operation.DELETED
        self.references['reject_reason'] = reason
        self.save(update_fields=('status', 'references'))

    @property
    def is_committed(self):
        return self.status == self.COMMITTED

    @property
    def is_cancelled(self):
        return self.status == self.CANCELLED

    def get_per_asset_balances(self):
        balance_annotation = Sum(
            'account__transaction__amount',
        )
        qs = Asset.objects.filter(account__transaction__operation=self) \
            .annotate(balance=balance_annotation)

        for asset in qs:
            yield asset, asset.balance or 0


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
            if self.account.type == Account.TYPE_ACTIVE and self.amount < 0:
                raise AccountStrictnessException(
                    self,
                    "Negative amount transaction on strictly active account."
                )
            if self.account.type == Account.TYPE_PASSIVE and self.amount > 0:
                raise AccountStrictnessException(
                    self,
                    "Positive amount transaction on strictly passive account."
                )
        return True
