from decimal import Decimal
from typing import Dict

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from django_banking.models import (
    Account,
    Asset,
    Operation
)
from django_banking.models.accounts.enum import AccountType
from django_banking.models.transactions.enum import OperationMethod
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

    def for_customer(self, user: AbstractBaseUser) -> 'ColdBankAccount':  # type: ignore # NOQA
        """Get deposit bank account for provided user.

        Bank account and currency choose based on user residency.
        """
        # TODO support fiat selection if available. not only the main one
        asset = Asset.objects.main_fiat_for_customer(user)
        return self.get(is_active=True, account__asset=asset)


class DepositWireTransferOperationManager(OperationManager):
    def create_deposit(self,
                       payment_method_account: Account,
                       user_account: Account,
                       amount: Decimal,
                       method: str = OperationMethod.OTHER,
                       fee_account: Account = None,
                       fee_amount: Decimal = None,
                       rounding_account: Account = None,
                       rounding_amount: Decimal = None,
                       references: Dict = None,
                       hold: bool = True,
                       metadata: Dict = None) -> 'Operation':
        if not references or 'user_bank_account_uuid' not in references:
            raise ValueError("Bank account ID must be provided")
        method = OperationMethod.WIRE_TRANSFER
        return super().create_deposit(
            payment_method_account=payment_method_account,
            user_account=user_account,
            amount=amount,
            method=method,
            fee_account=fee_account,
            fee_amount=fee_amount,
            rounding_account=rounding_account,
            rounding_amount=rounding_amount,
            references=references,
            hold=hold,
            metadata=metadata,
        )

    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_wire_transfer()


class WithdrawalWireTransferOperationManager(OperationManager):
    def create_withdrawal(self, *args, **kwargs) -> 'Operation':
        kwargs['method'] = OperationMethod.WIRE_TRANSFER
        return super().create_withdrawal(*args, **kwargs)

    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_wire_transfer()


class RefundWireTransferOperationManager(OperationManager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).refund_wire_transfer()
