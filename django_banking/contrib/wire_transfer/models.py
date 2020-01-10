from uuid import uuid4

from django.db import models
from django.utils.functional import cached_property

from django_banking import module_name
from django_banking.contrib.wire_transfer.managers import (
    BankAccountManager,
    DepositBankAccountManager,
    DepositWireTransferOperationManager,
    WithdrawalWireTransferOperationManager
)
from django_banking.models import (
    Account,
    Operation
)
from django_banking.settings import USER_MODEL


class ColdBankAccount(models.Model):

    """Deposit bank account model.

    Used to represent Business owned bank account to be shown to the user after
    wire_transfer-transfer deposit request created. User should transfer he's funds to
    this bank account if he want to deposit.

    There is only one active deposit bank account per fiat currency.
    """

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    is_active = models.BooleanField(default=False)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    bank_account_details = models.TextField()

    objects = DepositBankAccountManager()

    class Meta:
        db_table = f'{module_name}_coldbankaccount'

    def __str__(self):
        return f"{self.uuid} - {self.account.asset} ({self.is_active})"


class UserBankAccount(models.Model):
    """Bank account model for API.
    """

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)
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

    class Meta:
        db_table = f'{module_name}_userbankaccount'


class DepositWireTransferOperation(Operation):
    objects = DepositWireTransferOperationManager()

    class Meta:
        proxy = True

    @cached_property
    def amount(self):
        return self.references['amount']

    @cached_property
    def reference_code(self):
        return self.references['reference_code']


class WithdrawalWireTransferOperation(DepositWireTransferOperation):
    objects = WithdrawalWireTransferOperationManager()

    class Meta:
        proxy = True
