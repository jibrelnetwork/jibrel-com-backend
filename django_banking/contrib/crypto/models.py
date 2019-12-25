from uuid import uuid4

from django.db import models

from django_banking import module_name
from django_banking.settings import USER_MODEL

from .managers import (
    CryptoAccountManager,
    DepositCryptoAccountManager,
    DepositCryptoOperationManager,
    WithdrawalCryptoOperationManager
)
from ...models import Operation, Account


class CryptoAccount(models.Model):
    """Cryptocurrency account for API.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    is_active = models.BooleanField(default=True)

    #: bookkeeping account (accounting)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    address = models.CharField(max_length=128)

    objects = CryptoAccountManager()

    class Meta:
        db_table = f'{module_name}_cryptoaccount'

    def __str__(self):
        return f"{self.account.asset} - {self.address} ({self.user})"


class DepositCryptoAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT, null=True)

    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    address = models.CharField(max_length=128, unique=True, db_index=True)

    objects = DepositCryptoAccountManager()

    class Meta:
        db_table = f'{module_name}_depositcryptoaccount'

    def __str__(self):
        return f"{self.account.asset} - {self.address} ({self.user})"


class DepositCryptoOperation(Operation):
    objects = DepositCryptoOperationManager()

    class Meta:
        proxy = True

    def __str__(self):
        return f'DepositCryptoOperation({self.pk})'


class WithdrawalCryptoOperation(Operation):
    objects = WithdrawalCryptoOperationManager()

    class Meta:
        proxy = True
