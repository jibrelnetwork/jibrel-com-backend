import logging
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import UniqueConstraint

from jibrel.accounting.models import (
    Account,
    Operation
)
from jibrel.authentication.models import User
from jibrel.core.common.helpers import lazy
from jibrel.core.storages import operation_upload_storage
from jibrel.payments.helpers import BaseUserAccountManager

from .managers import (
    BankAccountManager,
    CardAccountManager,
    CryptoAccountManager,
    DepositCardOperationManager,
    DepositCryptoAccountManager,
    DepositCryptoOperationManager,
    DepositWireTransferOperationManager,
    UserAccountManager,
    WithdrawalCardOperationManager,
    WithdrawalCryptoOperationManager,
    WithdrawalWireTransferOperationManager
)
from .queryset import PaymentOperationQuerySet

logger = logging.getLogger(__name__)


class OperationConfirmationDocument(models.Model):
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT)
    file = models.FileField(storage=operation_upload_storage)
    created_at = models.DateTimeField(auto_now_add=True)


class DepositBankAccountManager(models.Manager):

    """DepositBankAccount model manager.
    """

    def for_customer(self, user: AbstractBaseUser) -> 'DepositBankAccount':
        """Get deposit bank account for provided user.

        Bank account and currency choose based on user residency.
        """
        asset = Asset.objects.get(country=user.get_residency_country_code())
        return self.get(is_active=True, account__asset=asset)


class DepositBankAccount(models.Model):

    """Deposit bank account model.

    Used to represent CoinMENA-owned bank account to be shown to the user after
    wire-transfer deposit request created. User should transfer he's funds to
    this bank account if he want to deposit.

    There is only one active deposit bank account per fiat currency.
    """

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    is_active = models.BooleanField(default=False)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    bank_account_details = models.TextField()

    objects = DepositBankAccountManager()

    def __str__(self):
        return f"{self.uuid} - {self.account.asset} ({self.is_active})"


class Fee(models.Model):
    VALUE_TYPE_CONSTANT = 'constant'
    VALUE_TYPE_PERCENTAGE = 'percentage'

    VALUE_TYPE_CHOICES = (
        (VALUE_TYPE_CONSTANT, 'Constant'),
        (VALUE_TYPE_PERCENTAGE, 'Percentage'),
    )

    OPERATION_TYPE_WITHDRAWAL_CRYPTO = 'withdrawal_crypto'
    OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT = 'withdrawal_bank_account'
    OPERATION_TYPE_DEPOSIT_CRYPTO = 'deposit_crypto'
    OPERATION_TYPE_DEPOSIT_BANK_ACCOUNT = 'deposit_bank_account'
    OPERATION_TYPE_DEPOSIT_CARD = 'deposit_card'

    OPERATION_TYPE_CHOICES = (
        (OPERATION_TYPE_WITHDRAWAL_CRYPTO, 'Withdrawal crypto'),
        (OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, 'Withdrawal bank account'),
        (OPERATION_TYPE_DEPOSIT_CRYPTO, 'Deposit crypto'),
        (OPERATION_TYPE_DEPOSIT_BANK_ACCOUNT, 'Deposit bank account'),
        (OPERATION_TYPE_DEPOSIT_CARD, 'Deposit card'),
    )
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation_type = models.CharField(max_length=30, choices=OPERATION_TYPE_CHOICES)
    asset = models.ForeignKey(Asset, null=True, on_delete=models.CASCADE)
    value_type = models.CharField(max_length=30, choices=VALUE_TYPE_CHOICES)
    value = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=settings.ACCOUNTING_DECIMAL_PLACES
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['asset', 'operation_type'], name='unique_asset_and_operation_type',
            )
        ]

    def calculate(self, amount: Decimal) -> Decimal:
        if self.value_type == Fee.VALUE_TYPE_CONSTANT:
            return self.value
        elif self.value_type == Fee.VALUE_TYPE_PERCENTAGE:
            return self.value * amount
        raise ValueError('You must specify value_type')


class TapCharge(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, null=True)

    charge_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)





class AbstractUserAccount(models.Model):

    """User asset bookkeeping account.

    Customer may have single account per asset.
    """
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    objects = UserAccountManager()

    class Meta:
        abstract = True


class UserAccount(AbstractUserAccount):
    """User to bookkeeping account relation for API.
    """


class BankAccount(models.Model):
    """Bank account model for API.
    """

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    is_active = models.BooleanField(default=True)

    #: bookkeeping account (accounting)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    #: ISO 9362 bank SWIFT identifier
    swift_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=200)
    holder_name = models.CharField(max_length=200)
    #: ISO 13616-1:2007 international bank account number
    iban_number = models.CharField(max_length=34)

    objects = BankAccountManager()


class CryptoAccount(models.Model):
    """Cryptocurrency account for API.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    is_active = models.BooleanField(default=True)

    #: bookkeeping account (accounting)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    address = models.CharField(max_length=128)

    objects = CryptoAccountManager()

    def __str__(self):
        return f"{self.account.asset} - {self.address} ({self.user})"


class DepositCryptoAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT, null=True)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    address = models.CharField(max_length=128, unique=True, db_index=True)

    objects = DepositCryptoAccountManager()

    def __str__(self):
        return f"{self.account.asset} - {self.address} ({self.user})"


class CardAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    tap_card_id = models.CharField(max_length=50, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    objects = CardAccountManager()


class FeeUserAccount(AbstractUserAccount):
    """Fee account for user"""

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=Account.TYPE_ACTIVE, strict=True))


class ExchangeUserAccount(AbstractUserAccount):
    """Account for exchange operations for user"""

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=Account.TYPE_NORMAL, strict=False))


class RoundingUserAccount(AbstractUserAccount):
    """Account for rounding remains in operations for user"""

    user = models.ForeignKey(to='authentication.User', on_delete=models.PROTECT)

    objects = BaseUserAccountManager(account_creation_kwargs=dict(type=Account.TYPE_NORMAL, strict=False))


class PaymentOperation(Operation):
    objects = PaymentOperationQuerySet.as_manager()

    class Meta:
        proxy = True


class OperationMixin:
    @lazy
    def user(self):
        return User.objects.filter(
            useraccount__account__transaction__operation_id=self.pk
        ).first()

    @lazy
    def bank_account(self):
        try:
            user_bank_account_id = self.references.get('user_bank_account_uuid')
            return BankAccount.objects.filter(pk=user_bank_account_id).first()
        except ObjectDoesNotExist:
            return None

    @lazy
    def card_account(self):
        try:
            return CardAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None

    @lazy
    def cryptocurrency_address(self):
        try:
            return CryptoAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None

    @lazy
    def deposit_cryptocurrency_address(self):
        try:
            return DepositCryptoAccount.objects.get(
                account__transaction__operation=self
            )
        except ObjectDoesNotExist:
            return None

    class Meta:
        abstract = True


class DepositCryptoOperation(OperationMixin, Operation):
    objects = DepositCryptoOperationManager()

    class Meta:
        proxy = True

    def __str__(self):
        return f'DepositCryptoOperation({self.pk})'


class DepositWireTransferOperation(OperationMixin, Operation):
    class Meta:
        proxy = True

    objects = DepositWireTransferOperationManager()


class WithdrawalWireTransferOperation(OperationMixin, Operation):
    class Meta:
        proxy = True

    objects = WithdrawalWireTransferOperationManager()


class WithdrawalCryptoOperation(OperationMixin, Operation):
    class Meta:
        proxy = True

    objects = WithdrawalCryptoOperationManager()


class DepositCardOperation(OperationMixin, Operation):
    class Meta:
        proxy = True

    objects = DepositCardOperationManager()


class WithdrawalCardOperation(OperationMixin, Operation):
    class Meta:
        proxy = True

    objects = WithdrawalCardOperationManager()
