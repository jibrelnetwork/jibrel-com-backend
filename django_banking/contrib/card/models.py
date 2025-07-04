from uuid import uuid4

from django.db import models

from django_banking import module_name

from ...models import (
    Account,
    Operation
)
from ...settings import USER_MODEL
from .managers import (
    CardAccountManager,
    DepositCardOperationManager,
    WithdrawalCardOperationManager
)


class UserCardAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    tap_card_id = models.CharField(max_length=50, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    objects = CardAccountManager()

    class Meta:
        db_table = f'{module_name}_usercardaccount'


class DepositCardOperation(Operation):
    objects = DepositCardOperationManager()

    class Meta:
        proxy = True


class WithdrawalCardOperation(Operation):
    objects = WithdrawalCardOperationManager()

    class Meta:
        proxy = True
