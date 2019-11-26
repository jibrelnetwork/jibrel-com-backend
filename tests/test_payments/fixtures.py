from decimal import Decimal

import pytest

from jibrel.authentication.models import User
from jibrel.payments.models import UserAccount
from jibrel.accounting.factories import AccountFactory
from jibrel.accounting import Asset, Operation


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
