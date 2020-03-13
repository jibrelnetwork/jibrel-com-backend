from decimal import Decimal
from typing import Dict

from django_banking.models import Operation, Account
from django_banking.models.transactions.enum import OperationMethod
from django_banking.models.transactions.managers import OperationManager
from django_banking.models.transactions.queryset import OperationQuerySet


class DepositCardOperationManager(OperationManager):
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
        if not references or 'checkout_token' not in references:  # todo backend selection or check all possible backends
            raise ValueError("Bank account ID must be provided")
        method = OperationMethod.CARD
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
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_card()


class WithdrawalCardOperationManager(OperationManager):
    def create_withdrawal(self, *args, **kwargs) -> 'Operation':
        kwargs['method'] = OperationMethod.CARD
        return super().create_withdrawal(*args, **kwargs)

    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_card()


class RefundCardOperationManager(OperationManager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).refund_card()
