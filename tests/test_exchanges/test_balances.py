from decimal import Decimal
from unittest.mock import call
from uuid import UUID

import pytest

from jibrel.accounting import Asset
from jibrel.exchanges import MarketBalanceLimit
from jibrel.exchanges.balance import (
    Balance,
    MarketBalanceException,
    _get_balances_from_kraken,
    _sanitize_decimal,
    update_balances,
    validate,
    validate_unprocessed_orders
)
from jibrel.exchanges.markets.private_kraken import private_kraken_api
from jibrel.exchanges.models import (
    ActionType,
    MarketOrder
)


@pytest.mark.parametrize(
    'given,default,expected',
    (
        ('1', Decimal(0), Decimal(1)),
        ('100000000', Decimal(0), Decimal(100000000)),
        ('0.0000001', Decimal(0), Decimal('0.0000001')),
        ('0.00001000', Decimal(0), Decimal('0.00001000')),
        ('-1', Decimal(0), Decimal(-1)),
        ('0', Decimal(0), Decimal(0)),
        ('-0', Decimal(0), Decimal(0)),
        ('sNaN', Decimal(0), Decimal(0)),
        ('-sNan', Decimal(0), Decimal(0)),
        ('Nan', Decimal(0), Decimal(0)),
        ('-nan', Decimal(0), Decimal(0)),
        ('infinity', Decimal(0), Decimal(0)),
        ('inf', Decimal(0), Decimal(0)),
        ('-infinity', Decimal(0), Decimal(0)),
        ('-inf', Decimal(0), Decimal(0)),
        ('some_text', Decimal(0), Decimal(0)),
    )
)
def test__sanitize_decimal(given, default, expected):
    assert _sanitize_decimal(given, default) == expected


@pytest.mark.parametrize(
    'response,expected',
    (
        (
            {"error": [], "result": {
                "ZUSD": "1",
                "XETH": "1",
                "XXBT": "1",
                "BCH": "1",
                "XLTC": "1",
                "XXRP": "1",
            }},
            [
                Balance('USD', Decimal(1)),
                Balance('ETH', Decimal(1)),
                Balance('BTC', Decimal(1)),
                Balance('BCH', Decimal(1)),
                Balance('LTC', Decimal(1)),
                Balance('XRP', Decimal(1)),
            ]
        ),
        (
            {"error": [], "result": {
                "ZUSD": "0",
                "XETH": "0",
                "XXBT": "0",
                "BCH": "0",
                "XLTC": "0",
                "XXRP": "0",
            }},
            [
                Balance('USD', Decimal(0)),
                Balance('ETH', Decimal(0)),
                Balance('BTC', Decimal(0)),
                Balance('BCH', Decimal(0)),
                Balance('LTC', Decimal(0)),
                Balance('XRP', Decimal(0)),
            ]
        ),
        (
            {"error": [], "result": {"ZUSD": "17.2496", "XETH": "0.8988264000"}},
            [Balance('USD', Decimal('17.2496')), Balance('ETH', Decimal('0.8988264000'))]
        ),
        (
            {"error": [], "result": {"ZUSD": "100000", "JNT": "100"}},
            [Balance('USD', Decimal('100000'))]
        ),

    )
)
def test__get_balances_from_kraken(mocker, response, expected):
    mocker.patch.object(private_kraken_api, 'get_account_balance', return_value=response)
    assert _get_balances_from_kraken() == expected


@pytest.mark.parametrize(
    'balances,expected',
    (
        (
            [
                Balance('USD', Decimal(0)),
                Balance('BTC', Decimal(0)),
                Balance('ETH', Decimal(0)),
                Balance('XRP', Decimal(0)),
                Balance('LTC', Decimal(0)),
                Balance('BCH', Decimal(0)),
            ],
            [
                (UUID('72fd37b0-a579-4145-bf35-b1902d505a0c'), Decimal(0)),
                (UUID('1ef78ac6-f958-4a68-85ac-c78c83871abe'), Decimal(0)),
                (UUID('7e6a5e51-012d-4a2a-bd8b-8b6787fb0038'), Decimal(0)),
                (UUID('653efbf6-a8f9-4085-807a-3b494dc9ae3b'), Decimal(0)),
                (UUID('3e235a34-dfbf-4752-922e-9bee4972cf41'), Decimal(0)),
                (UUID('a48a4b34-7df7-4b81-8ed4-3437eaaee2a2'), Decimal(0)),
            ]
        ),
        (
            [
                Balance('USD', Decimal('0.000123')),
                Balance('BTC', Decimal('0.000123')),
                Balance('ETH', Decimal('0.000123')),
                Balance('XRP', Decimal('0.000123')),
                Balance('LTC', Decimal('0.000123')),
                Balance('BCH', Decimal('0.000123')),
            ],
            [
                (UUID('72fd37b0-a579-4145-bf35-b1902d505a0c'), Decimal('0.000123')),
                (UUID('1ef78ac6-f958-4a68-85ac-c78c83871abe'), Decimal('0.000123')),
                (UUID('7e6a5e51-012d-4a2a-bd8b-8b6787fb0038'), Decimal('0.000123')),
                (UUID('653efbf6-a8f9-4085-807a-3b494dc9ae3b'), Decimal('0.000123')),
                (UUID('3e235a34-dfbf-4752-922e-9bee4972cf41'), Decimal('0.000123')),
                (UUID('a48a4b34-7df7-4b81-8ed4-3437eaaee2a2'), Decimal('0.000123')),
            ]
        ),
        (
            [
                Balance('USD', Decimal('1000')),
            ],
            [
                (UUID('72fd37b0-a579-4145-bf35-b1902d505a0c'), Decimal('1000')),
            ]
        ),
        (
            [],
            []
        ),
    )
)
@pytest.mark.django_db
def test_update_balances(balances, expected, mocker):
    mocked_cache = mocker.patch('jibrel.exchanges.balance.cache')
    mocker.patch('jibrel.exchanges.balance._get_balances_from_kraken', return_value=balances)
    update_balances()
    calls = [
        call(*e)
        for e in expected
    ]

    mocked_cache.__setitem__.assert_has_calls(calls)


@pytest.mark.parametrize(
    'raise_value,balance,amount',
    (
        (Decimal(1000), Decimal(10000), Decimal(100)),
        (Decimal(1000), Decimal(1100), Decimal(100)),
        (Decimal(1), Decimal('1.1'), Decimal('0.1')),
        (Decimal(0), Decimal(1000), Decimal(100)),
        pytest.param(
            Decimal(1000), Decimal(1000), Decimal(100),
            marks=pytest.mark.xfail(strict=True, raises=MarketBalanceException)
        ),
        pytest.param(
            Decimal(10000), Decimal(1000), Decimal(100),
            marks=pytest.mark.xfail(strict=True, raises=MarketBalanceException)
        ),
        pytest.param(
            Decimal(100), Decimal(1000), Decimal(1001),
            marks=pytest.mark.xfail(strict=True, raises=MarketBalanceException)
        )
    )
)
def test_validate(raise_value, balance, amount, mocker):
    limit = MarketBalanceLimit(raise_value=raise_value)
    mocker.patch.object(MarketBalanceLimit.objects, 'get', return_value=limit)
    mocked_cache = mocker.patch('jibrel.exchanges.balance.cache')
    mocked_cache.__getitem__.return_value = balance
    validate(mocker.Mock(), amount)


@pytest.mark.parametrize('order_per_user', (1, 2, 5))
@pytest.mark.parametrize('n_sell,n_buy', ((1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 2)))
@pytest.mark.parametrize('country', ('AE', 'BH',))
@pytest.mark.parametrize('crypto_asset_symbol', ('LTC', 'XRP'))
@pytest.mark.django_db
def test_get_amounts_per_asset(
    country,
    crypto_asset_symbol,
    n_sell,
    n_buy,
    order_per_user,
    full_verified_user_factory,
    create_prepared_exchange_operation,
):
    crypto_amount = Decimal(1)

    crypto_to_intermediate_price = Decimal(10000)
    crypto_asset = Asset.objects.get(symbol=crypto_asset_symbol)

    intermediate_to_fiat_price = Decimal(3)
    intermediate_asset = Asset.objects.get(symbol='USD')

    user = full_verified_user_factory(country)
    u_cnt = 0

    for i in range(n_sell):
        action_type = ActionType.SELL
        if u_cnt == order_per_user:
            user = full_verified_user_factory(country)
            u_cnt = 0

        fiat_asset = Asset.objects.main_fiat_for_customer(user)

        create_prepared_exchange_operation(
            user=user,
            action_type=action_type,
            crypto_asset=crypto_asset,
            fiat_asset=fiat_asset,
            crypto_amount=crypto_amount,
            crypto_to_intermediate_price=crypto_to_intermediate_price,
            intermediate_to_fiat_price=intermediate_to_fiat_price,
            commit=False,
        )
        u_cnt += 1

    for i in range(n_buy):
        action_type = ActionType.BUY
        if u_cnt == order_per_user:
            user = full_verified_user_factory(country)
            u_cnt = 0

        fiat_asset = Asset.objects.main_fiat_for_customer(user)

        create_prepared_exchange_operation(
            user=user,
            action_type=action_type,
            crypto_asset=crypto_asset,
            fiat_asset=fiat_asset,
            crypto_amount=crypto_amount,
            crypto_to_intermediate_price=crypto_to_intermediate_price,
            intermediate_to_fiat_price=intermediate_to_fiat_price,
            commit=False,
        )
        u_cnt += 1


    amounts_per_asset = dict(MarketOrder.objects.get_amounts_per_asset())
    if n_sell:
        assert amounts_per_asset[crypto_asset.pk] == crypto_amount * n_sell
    if n_buy:
        assert amounts_per_asset[intermediate_asset.pk] == crypto_amount * crypto_to_intermediate_price * n_buy


@pytest.mark.parametrize('action_type', (ActionType.BUY, ActionType.SELL))
@pytest.mark.django_db
def test_validate_unprocessed_orders(
    action_type,
    create_prepared_exchange_operation,
    full_verified_user,
    mocker,
):
    validate_unprocessed_orders()

    crypto_asset = Asset.objects.get(symbol='BTC')

    create_prepared_exchange_operation(
        user=full_verified_user,
        action_type=action_type,
        crypto_asset=crypto_asset,
        fiat_asset=Asset.objects.main_fiat_for_customer(full_verified_user),
        crypto_amount=Decimal(1),
        crypto_to_intermediate_price=Decimal(10000),
        intermediate_to_fiat_price=Decimal(3),
        commit=False,
    )

    mocked = mocker.patch('jibrel.exchanges.balance.validate')

    validate_unprocessed_orders()

    mocked.side_effect = MarketBalanceException

    with pytest.raises(MarketBalanceException):
        validate_unprocessed_orders()
