import pytest

from ccwt.exceptions import (
    AccountBalanceException,
    AccountStrictnessException,
    OperationBalanceException
)
from jibrel.accounting.models import (
    Account,
    Asset,
    Operation
)


@pytest.mark.django_db
def test_success_operation_commit():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_ACTIVE, strict=True, asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=True, asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)
    op.transactions.create(account=acc1, amount=10)
    with pytest.raises(OperationBalanceException):
        op.is_valid()

    op.transactions.create(account=acc2, amount=-10)
    assert op.is_valid()
    op.hold()
    op.commit()


@pytest.mark.django_db
def test_active_account_negative_balance():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_ACTIVE, strict=False, asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False, asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=-10)
    op.transactions.create(account=acc2, amount=10)

    with pytest.raises(AccountBalanceException):
        op.is_valid()

    with pytest.raises(AccountBalanceException):
        op.hold()


@pytest.mark.django_db
def test_passive_account_positive_balance():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_PASSIVE, strict=False,
                                  asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False,
                                  asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=10)
    op.transactions.create(account=acc2, amount=-10)

    with pytest.raises(AccountBalanceException):
        op.is_valid()

    with pytest.raises(AccountBalanceException):
        op.hold()


@pytest.mark.django_db
def test_active_strictness():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_PASSIVE, strict=True,
                                  asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False,
                                  asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=10)
    op.transactions.create(account=acc2, amount=-10)

    with pytest.raises(AccountStrictnessException):
        op.is_valid()


@pytest.mark.django_db
def test_passive_strictness():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_ACTIVE, strict=True,
                                  asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False,
                                  asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=-10)
    op.transactions.create(account=acc2, amount=10)

    with pytest.raises(AccountStrictnessException):
        op.is_valid()


@pytest.mark.django_db
def test_conflicting_operations():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_ACTIVE, strict=False,
                                  asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False,
                                  asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=10)
    op.transactions.create(account=acc2, amount=-10)

    assert op.is_valid()
    op.hold()
    op.commit()

    op2 = Operation.objects.create(type=Operation.WITHDRAWAL)

    op2.transactions.create(account=acc1, amount=-10)
    op2.transactions.create(account=acc2, amount=10)

    op3 = Operation.objects.create(type=Operation.WITHDRAWAL)
    op3.transactions.create(account=acc1, amount=-10)
    op3.transactions.create(account=acc2, amount=10)

    with pytest.raises(AccountBalanceException):
        op2.is_valid()

    with pytest.raises(AccountBalanceException):
        op3.is_valid()


@pytest.mark.django_db
def test_conflict_with_holded_operation():
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=Account.TYPE_ACTIVE, strict=False,
                                  asset=asset)
    acc2 = Account.objects.create(type=Account.TYPE_NORMAL, strict=False,
                                  asset=asset)

    op = Operation.objects.create(type=Operation.DEPOSIT)

    op.transactions.create(account=acc1, amount=10)
    op.transactions.create(account=acc2, amount=-10)

    assert op.is_valid()

    op.hold()
    op.commit()

    op2 = Operation.objects.create(type=Operation.WITHDRAWAL)
    op2.transactions.create(account=acc1, amount=-10)
    op2.transactions.create(account=acc2, amount=10)

    assert op2.is_valid()
    op2.hold()

    op3 = Operation.objects.create(type=Operation.WITHDRAWAL)
    op3.transactions.create(account=acc1, amount=-10)
    op3.transactions.create(account=acc2, amount=10)

    with pytest.raises(AccountBalanceException):
        op3.is_valid()

    assert op2.is_valid(include_new=False)
    op2.commit()
