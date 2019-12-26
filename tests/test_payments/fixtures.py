from decimal import Decimal

import pytest

from django_banking.models import UserAccount, Operation, Asset
from ..test_banking.factories.dajngo_banking import AccountFactory
from jibrel.authentication.models import User


@pytest.fixture()
def create_deposit_operation(db):
    def _create_deposit_operation(
        user: User,
        asset: Asset,
        amount: Decimal,
        commit: bool = True,
    ):
        payment_account = AccountFactory.create(asset=asset)
        user_account = UserAccount.objects.for_customer(user, asset)
        operation = Operation.objects.create_deposit(
            payment_method_account=payment_account,
            user_account=user_account,
            amount=amount,
        )
        if commit:
            operation.commit()
        return operation

    return _create_deposit_operation
