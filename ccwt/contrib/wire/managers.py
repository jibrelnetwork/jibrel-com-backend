from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from ccwt.models import Asset, Account
from ccwt.models.accounts.enum import AccountType
from ccwt.models.transactions.queryset import OperationQuerySet


class BankAccountManager(models.Manager):
    def create(self, **kwargs):
        if 'account' not in kwargs:
            asset = Asset.objects.get(country=kwargs['user'].get_residency_country_code())
            kwargs['account'] = Account.objects.create(
                asset=asset, type=AccountType.TYPE_NORMAL, strict=False
            )
        return super().create(**kwargs)


class DepositBankAccountManager(models.Manager):

    """DepositBankAccount model manager.
    """

    def for_customer(self, user: AbstractBaseUser) -> 'DepositBankAccount':
        """Get deposit bank account for provided user.

        Bank account and currency choose based on user residency.
        """
        # TODO
        asset = Asset.objects.get(country=user.get_residency_country_code())
        return self.get(is_active=True, account__asset=asset)


class DepositWireTransferOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_wire_transfer()


class WithdrawalWireTransferOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_wire_transfer()

