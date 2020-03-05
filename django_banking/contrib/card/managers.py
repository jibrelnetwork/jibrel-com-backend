from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationMethod
from django_banking.models.transactions.managers import OperationManager
from django_banking.models.transactions.queryset import OperationQuerySet


class DepositCardOperationManager(OperationManager):
    def create_deposit(self, *args, **kwargs) -> 'Operation':
        kwargs['method'] = OperationMethod.CARD
        return super().create_deposit(*args, **kwargs)

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
