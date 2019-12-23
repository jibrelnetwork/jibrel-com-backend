from decimal import Decimal
from typing import (
    NamedTuple,
    Type
)

import pytest

from jibrel.accounting import (
    Account,
    Asset,
    Operation
)
from ccwt.exceptions import AccountBalanceException
from ccwt.tests.factories.factories import AccountFactory
from jibrel.exchanges.models import (
    ActionType,
    MarketOrder
)

D = Decimal


class ParametrizeArg(NamedTuple):
    id: str
    # given
    before_base_balance: Decimal
    before_quote_balance: Decimal

    # when
    quote_amount: Decimal
    base_amount: Decimal
    fee_amount: Decimal

    # then
    after_base_balance: Decimal
    after_quote_balance: Decimal


args = (
    # buy
    ParametrizeArg(
        id='w/o fee; q amount == q balance',
        before_base_balance=D(0),
        before_quote_balance=D(100),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(0),
        after_base_balance=D(1),
        after_quote_balance=D(0),
    ),
    ParametrizeArg(
        id='w/o fee; amount < balance',
        before_base_balance=D(0),
        before_quote_balance=D(150),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(0),
        after_base_balance=D(1),
        after_quote_balance=D(50),
    ),
    ParametrizeArg(
        id='w/ fee; amount + fee == balance',
        before_base_balance=D(0),
        before_quote_balance=D(100),
        quote_amount=D(-65),
        base_amount=D(1),
        fee_amount=D(35),
        after_base_balance=D(1),
        after_quote_balance=D(0),
    ),
    ParametrizeArg(
        id='w/ fee; amount + fee < balance',
        before_base_balance=D(0),
        before_quote_balance=D(150),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(35),
        after_base_balance=D(1),
        after_quote_balance=D(15),
    ),
    # sell
    ParametrizeArg(
        id='w/o fee; amount == balance',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(100),
        base_amount=D(-1),
        fee_amount=D(0),
        after_base_balance=D(0),
        after_quote_balance=D(100),
    ),
    ParametrizeArg(
        id='w/o fee; b amount < b balance',
        before_base_balance=D(2),
        before_quote_balance=D(0),
        quote_amount=D(100),
        base_amount=D(-1),
        fee_amount=D(0),
        after_base_balance=D(1),
        after_quote_balance=D(100),
    ),
    ParametrizeArg(
        id='w/ fee; q amount - q fee == 0',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(35),
        base_amount=D(-1),
        fee_amount=D(35),
        after_base_balance=D(0),
        after_quote_balance=D(0),
    ),
    ParametrizeArg(
        id='w/ fee; q amount - q fee > 0',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(100),
        base_amount=D(-1),
        fee_amount=D(35),
        after_base_balance=D(0),
        after_quote_balance=D(65),
    )
)


@pytest.mark.parametrize(
    'arg', args, ids=[arg.id for arg in args]
)
@pytest.mark.django_db
def test_positive_create_exchange(arg):
    base_account = AccountFactory.create(type=Account.TYPE_ACTIVE)
    base_exchange_account = AccountFactory.create(asset=base_account.asset)
    quote_account = AccountFactory.create(type=Account.TYPE_ACTIVE)
    quote_exchange_account = AccountFactory.create(asset=quote_account.asset)
    fee_account = AccountFactory.create(asset=quote_account.asset, type=Account.TYPE_ACTIVE, strict=True)

    if arg.before_base_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=base_account.asset),
            user_account=base_account,
            amount=arg.before_base_balance,
        ).commit()

    if arg.before_quote_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=quote_account.asset),
            user_account=quote_account,
            amount=arg.before_quote_balance,
        ).commit()

    Operation.objects.create_exchange(
        base_account=base_account,
        base_exchange_account=base_exchange_account,
        base_amount=arg.base_amount,
        quote_account=quote_account,
        quote_exchange_account=quote_exchange_account,
        quote_amount=arg.quote_amount,
        fee_account=fee_account,
        fee_amount=arg.fee_amount,
        base_rounding_account=AccountFactory.create(asset=base_account.asset),
        base_rounding_amount=Decimal(0),
        quote_rounding_account=AccountFactory.create(asset=quote_account.asset),
        quote_rounding_amount=Decimal(0),
    ).commit()

    assert base_account.calculate_balance() == arg.after_base_balance
    assert quote_account.calculate_balance() == arg.after_quote_balance


class ParametrizeArg(NamedTuple):
    id: str
    # given
    before_base_balance: Decimal
    before_quote_balance: Decimal

    # when
    quote_amount: Decimal
    base_amount: Decimal
    fee_amount: Decimal

    # then
    exception: Type[Exception]


args = (
    # buy
    ParametrizeArg(
        id='buy: w/o fee; balance < amount',
        before_base_balance=D(0),
        before_quote_balance=D(10),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(0),
        exception=AccountBalanceException
    ),
    ParametrizeArg(
        id='buy: w/ fee; balance == amount; balance < (amount + fee) ',
        before_base_balance=D(0),
        before_quote_balance=D(100),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(35),
        exception=AccountBalanceException
    ),
    ParametrizeArg(
        id='buy: w/ fee; balance < amount; balance < (amount + fee) ',
        before_base_balance=D(0),
        before_quote_balance=D(10),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(35),
        exception=AccountBalanceException
    ),
    # sell
    ParametrizeArg(
        id='sell: w/o fee; b balance < b amount',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(10),
        base_amount=D(-2),
        fee_amount=D(0),
        exception=AccountBalanceException
    ),
    ParametrizeArg(
        id='sell: w/ fee; balance == amount; balance < (amount + fee) ',
        before_base_balance=D(0),
        before_quote_balance=D(0),
        quote_amount=D(10),
        base_amount=D(-1),
        fee_amount=D(35),
        exception=AccountBalanceException
    ),
)


@pytest.mark.parametrize(
    'arg', args, ids=[arg.id for arg in args]
)
@pytest.mark.django_db
def test_negative_create_exchange(arg):
    base_account = AccountFactory.create(type=Account.TYPE_ACTIVE)
    base_exchange_account = AccountFactory.create(asset=base_account.asset)
    quote_account = AccountFactory.create(type=Account.TYPE_ACTIVE)
    quote_exchange_account = AccountFactory.create(asset=quote_account.asset)
    fee_account = AccountFactory.create(asset=quote_account.asset, type=Account.TYPE_ACTIVE, strict=True)

    if arg.before_base_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=base_account.asset),
            user_account=base_account,
            amount=arg.before_base_balance,
        ).commit()

    if arg.before_quote_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=quote_account.asset),
            user_account=quote_account,
            amount=arg.before_quote_balance,
        ).commit()

    assert quote_account.calculate_balance() == arg.before_quote_balance

    with pytest.raises(arg.exception):
        Operation.objects.create_exchange(
            base_account=base_account,
            base_exchange_account=base_exchange_account,
            base_amount=arg.base_amount,
            quote_account=quote_account,
            quote_exchange_account=quote_exchange_account,
            quote_amount=arg.quote_amount,
            fee_account=fee_account,
            fee_amount=arg.fee_amount,
            base_rounding_account=AccountFactory.create(asset=base_account.asset),
            base_rounding_amount=Decimal(0),
            quote_rounding_account=AccountFactory.create(asset=quote_account.asset),
            quote_rounding_amount=Decimal(0),
        ).commit()


class ParametrizeArg(NamedTuple):
    id: str
    # given
    before_base_balance: Decimal
    before_quote_balance: Decimal

    # when
    quote_amount: Decimal
    base_amount: Decimal
    fee_amount: Decimal

    # then
    hold_base_balance: Decimal
    hold_quote_balance: Decimal
    commit_base_balance: Decimal
    commit_quote_balance: Decimal


args = (
    # buy
    ParametrizeArg(
        id='buy: w/o fee; balance == amount',
        before_base_balance=D(0),
        before_quote_balance=D(100),
        quote_amount=D(-100),
        base_amount=D(1),
        fee_amount=D(0),
        hold_base_balance=D(0),
        hold_quote_balance=D(0),
        commit_base_balance=D(1),
        commit_quote_balance=D(0),
    ),
    ParametrizeArg(
        id='buy: w/ fee; balance == (amount + fee)',
        before_base_balance=D(0),
        before_quote_balance=D(100),
        quote_amount=D(-65),
        base_amount=D(1),
        fee_amount=D(35),
        hold_base_balance=D(0),
        hold_quote_balance=D(0),
        commit_base_balance=D(1),
        commit_quote_balance=D(0),
    ),
    # sell
    ParametrizeArg(
        id='sell: w/o fee; b balance == b amount',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(100),
        base_amount=D(-1),
        fee_amount=D(0),
        hold_base_balance=D(0),
        hold_quote_balance=D(0),
        commit_base_balance=D(0),
        commit_quote_balance=D(100),
    ),
    ParametrizeArg(
        id='sell: w/ fee; balance == amount; balance == (amount + fee) ',
        before_base_balance=D(1),
        before_quote_balance=D(0),
        quote_amount=D(100),
        base_amount=D(-1),
        fee_amount=D(35),
        hold_base_balance=D(0),
        hold_quote_balance=D(0),
        commit_base_balance=D(0),
        commit_quote_balance=D(65),
    ),
)


@pytest.mark.parametrize(
    'arg', args, ids=[arg.id for arg in args]
)
@pytest.mark.django_db
def test_positive_with_amounts(arg):
    base_account = AccountFactory.create(type=Account.TYPE_ACTIVE, asset__type=Asset.CRYPTO)
    base_exchange_account = AccountFactory.create(asset=base_account.asset)
    quote_account = AccountFactory.create(type=Account.TYPE_ACTIVE, asset__type=Asset.FIAT)
    quote_exchange_account = AccountFactory.create(asset=quote_account.asset)
    fee_account = AccountFactory.create(asset=quote_account.asset, type=Account.TYPE_ACTIVE, strict=True)

    if arg.before_base_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=base_account.asset),
            user_account=base_account,
            amount=arg.before_base_balance,
        ).commit()

    if arg.before_quote_balance > 0:
        Operation.objects.create_deposit(
            payment_method_account=AccountFactory.create(asset=quote_account.asset),
            user_account=quote_account,
            amount=arg.before_quote_balance,
        ).commit()

    assert Account.objects.with_balances().get(pk=base_account.pk).balance == arg.before_base_balance
    assert Account.objects.with_balances().get(pk=quote_account.pk).balance == arg.before_quote_balance

    operation = Operation.objects.create_exchange(
        base_account=base_account,
        base_exchange_account=base_exchange_account,
        base_amount=arg.base_amount,
        quote_account=quote_account,
        quote_exchange_account=quote_exchange_account,
        quote_amount=arg.quote_amount,
        fee_account=fee_account,
        fee_amount=arg.fee_amount,
        base_rounding_account=AccountFactory.create(asset=base_account.asset),
        base_rounding_amount=Decimal(0),
        quote_rounding_account=AccountFactory.create(asset=quote_account.asset),
        quote_rounding_amount=Decimal(0),

        hold=True,
    )

    hold_base_acc = Account.objects.with_balances().get(pk=base_account.pk)
    hold_quote_acc = Account.objects.with_balances().get(pk=quote_account.pk)

    assert hold_base_acc.balance == arg.hold_base_balance
    assert hold_quote_acc.balance == arg.hold_quote_balance

    operation.commit()

    commit_base_acc = Account.objects.with_balances().get(pk=base_account.pk)
    commit_quote_acc = Account.objects.with_balances().get(pk=quote_account.pk)

    assert commit_base_acc.balance == arg.commit_base_balance
    assert commit_quote_acc.balance == arg.commit_quote_balance


@pytest.mark.parametrize(
    'action_type,country,cryptocurrency,crypto_amount,fiat_amount,' +
    'crypto_to_intermediate_price,intermediate_to_fiat_price',
    (
        (ActionType.BUY, 'AE', 'BTC', Decimal('0.02'), None, Decimal(10000), Decimal(3)),
        (ActionType.BUY, 'AE', 'BTC', None, Decimal(10000), Decimal(10000), Decimal(3)),
        (ActionType.SELL, 'AE', 'BTC', Decimal(1), None, Decimal(10000), Decimal(3)),
        (ActionType.SELL, 'AE', 'BTC', None, Decimal(10000), Decimal(10000), Decimal(3)),
    )
)
@pytest.mark.django_db
def test_create_exchange_operation(
    action_type,
    country,
    cryptocurrency,
    crypto_amount,
    fiat_amount,
    crypto_to_intermediate_price,
    intermediate_to_fiat_price,
    full_verified_user_factory,
    create_deposit_operation,
    create_exchange_operation,
):

    crypto_to_intermediate_price = Decimal(10000)
    intermediate_to_fiat_price = Decimal(3)

    user = full_verified_user_factory(country)

    fiat_asset = Asset.objects.main_fiat_for_customer(user)
    crypto_asset = Asset.objects.get(symbol=cryptocurrency)

    if action_type is ActionType.BUY:
        asset_to_deposit = fiat_asset
        if crypto_amount is not None:
            amount_to_deposit = (
                crypto_to_intermediate_price
                * intermediate_to_fiat_price
                * crypto_amount
            )
        else:
            amount_to_deposit = fiat_amount
    else:  # ActionType.SELL
        asset_to_deposit = crypto_asset
        if fiat_amount is not None:
            amount_to_deposit = (
                fiat_amount
                / crypto_to_intermediate_price
                / intermediate_to_fiat_price
            )
        else:
            amount_to_deposit = crypto_amount

    create_deposit_operation(
        user=user,
        asset=asset_to_deposit,
        amount=amount_to_deposit
    )

    operation = create_exchange_operation(
        user=user,
        action_type=action_type,
        crypto_asset=crypto_asset,
        fiat_asset=fiat_asset,
        crypto_amount=crypto_amount,
        fiat_amount=fiat_amount,
        crypto_to_intermediate_price=crypto_to_intermediate_price,
        intermediate_to_fiat_price=intermediate_to_fiat_price,
    )
    order = MarketOrder.objects.get(operation=operation)
    if crypto_amount:
        assert order.base_volume == crypto_amount
        assert order.predicted_quote_volume == crypto_amount * crypto_to_intermediate_price
