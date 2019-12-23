from decimal import Decimal
from typing import (
    Dict,
    List
)

from django.db import (
    models,
    transaction
)
from .enum import OperationStatus, OperationType

from .. import Account


class OperationManager(models.Manager):

    """Operations manager.

    Some of the methods requires to run only outside of db transaction to
    overcome transaction isolation.
    """

    def create_deposit(self,
                       payment_method_account: Account,
                       user_account: Account,
                       amount: Decimal,
                       fee_account: Account = None,
                       fee_amount: Decimal = None,
                       rounding_account: Account = None,
                       rounding_amount: Decimal = None,
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
                type=OperationType.DEPOSIT,
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
                          amount: Decimal,
                          fee_account: Account = None,
                          fee_amount: Decimal = None,
                          rounding_account: Account = None,
                          rounding_amount: Decimal = None,
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
                type=OperationType.WITHDRAWAL,
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
        base_amount: Decimal,
        quote_account: Account,
        quote_exchange_account: Account,
        quote_amount: Decimal,
        fee_account: Account,
        fee_amount: Decimal,
        base_rounding_account: Account = None,
        base_rounding_amount: Decimal = None,
        quote_rounding_account: Account = None,
        quote_rounding_amount: Decimal = None,
        references: Dict = None,
        hold: bool = True,
        metadata: Dict = None,
    ) -> 'Operation':
        assert base_amount * quote_amount < 0, 'Exchange operation must decrease one account and increase another'
        assert fee_amount >= 0, 'Fee can\'t be negative'
        with transaction.atomic():
            operation = self.create(
                type=OperationType.BUY if base_amount > 0 else OperationType.SELL,
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
                if operation.status != OperationStatus.HOLD:
                    operation.delete()
        return operation
