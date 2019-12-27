from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from django_banking.models.transactions.managers import OperationManager
from django_banking.models.transactions.queryset import OperationQuerySet


class BankAccountManager(models.Manager):
    def create(self, **kwargs):
        if 'account' not in kwargs:
            asset = Asset.objects.main_fiat_for_customer(kwargs['user'])
            kwargs['account'] = Account.objects.create(
                asset=asset, type=AccountType.TYPE_NORMAL, strict=False
            )
        return super().create(**kwargs)


class DepositBankAccountManager(models.Manager):

    """DepositBankAccount model manager.
    """

    def for_customer(self, user: AbstractBaseUser) -> 'ColdBankAccount':  # NOQA
        """Get deposit bank account for provided user.

        Bank account and currency choose based on user residency.
        """
        # TODO
        asset = Asset.objects.main_fiat_for_customer(user)
        return self.get(is_active=True, account__asset=asset)


class DepositWireTransferOperationManager(OperationManager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_wire_transfer()


class WithdrawalWireTransferOperationManager(OperationManager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_wire_transfer()
