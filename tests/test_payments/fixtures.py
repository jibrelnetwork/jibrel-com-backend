from decimal import Decimal

import pytest

from django_banking.contrib.card.models import DepositCardOperation
from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation,
    RefundWireTransferOperation,
    UserBankAccount
)
from django_banking.models import (
    Account,
    Asset,
    UserAccount
)
from django_banking.models.transactions.enum import OperationMethod
from jibrel.authentication.models import User

from ..test_banking.factories.dajngo_banking import AccountFactory
from ..test_banking.factories.wire_transfer import BankAccountFactory


@pytest.fixture()
def create_deposit_operation(db, create_user_bank_account):
    def _create_deposit_operation(
        amount: Decimal,
        method: str = OperationMethod.WIRE_TRANSFER,
        user: User = None,
        asset: Asset = None,
        payment_method_account: Account = None,
        user_account: Account = None,
        bank_account: UserBankAccount = None,
        commit: bool = True,
        references: dict = None,
    ):
        assert payment_method_account and user_account or asset and user
        payment_method_account = payment_method_account or AccountFactory.create(asset=asset)
        user_account = user_account or UserAccount.objects.for_customer(user, asset)
        user = user or UserAccount.objects.filter(account=user_account).first().user
        _references = {'reference_code': 'reference_code'}
        _references.update(references or {})
        if method == OperationMethod.WIRE_TRANSFER and 'user_bank_account_uuid' not in _references:
            bank_account = bank_account or create_user_bank_account(
                user=user,
                account=payment_method_account
            )
            _references['user_bank_account_uuid'] = str(bank_account.pk)
        model = DepositWireTransferOperation if method == OperationMethod.WIRE_TRANSFER else \
            DepositCardOperation
        operation = model.objects.create_deposit(
            payment_method_account=payment_method_account,
            user_account=user_account,
            amount=amount,
            references=_references,
            method=method
        )
        if commit:
            operation.commit()
        return operation

    return _create_deposit_operation


@pytest.fixture()
def deposit_operation(db, create_deposit_operation, full_verified_user, asset_usd):
    return create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17
    )


@pytest.fixture()
def create_refund_operation(db):
    def _create_refund_operation(
        amount: Decimal,
        deposit: DepositWireTransferOperation,
        commit: bool = True,
    ):
        operation = RefundWireTransferOperation.objects.create_refund(
            amount=amount,
            deposit=deposit
        )
        if commit:
            operation.commit()
        return operation

    return _create_refund_operation


@pytest.fixture()
def refund_operation(db, deposit_operation, create_refund_operation):
    return create_refund_operation(
        amount=17,
        deposit=deposit_operation
    )


@pytest.fixture()
def create_user_bank_account(db):
    def _create_user_bank_account(**kwargs):
        return BankAccountFactory.create(**kwargs)
    return _create_user_bank_account
