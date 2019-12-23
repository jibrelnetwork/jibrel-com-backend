from decimal import Decimal

import pytest
from hypothesis import (
    given,
    strategies
)
from rest_framework.test import APIClient

from jibrel.accounting import (
    Asset,
    Operation
)
from ccwt.tests.factories.factories import AssetFactory
from jibrel.assets import AssetPair
from jibrel.exchanges.models import (
    ActionType,
    Offer
)
from ccwt.tests.factories import (
    DepositBankAccountFactory,
    DepositCryptoAccountFactory
)
from jibrel.payments.models import UserAccount


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.fixture
def offer_factory():
    from jibrel.exchanges.repositories.offer import offer_repository

    def _offer_factory(
        asset_pair_id,
        action_type,
        base_amount,
        quote_amount,
        fee_amount,
        price=None,
    ):
        action_type = ActionType(action_type)
        if price is None:
            price = Decimal(1)
        return offer_repository.create(
            Offer(
                asset_pair_uuid=asset_pair_id,
                action_type=action_type,
                price=price,
                base_amount=base_amount,
                display_base_amount=base_amount,
                base_amount_unrounded=base_amount,
                quote_amount=quote_amount,
                display_quote_amount=quote_amount,
                quote_amount_unrounded=quote_amount,
                fee_amount=fee_amount,
                fee_amount_unrounded=fee_amount,
                display_total_amount=Decimal(1),
                intermediate_fiat_price=Decimal(1),
                intermediate_crypto_price=Decimal(1),
            )
        )

    return _offer_factory


@pytest.fixture
def user_with_fiat_balance(full_verified_user_factory):
    def _user_with_balance(country, amount):
        user = full_verified_user_factory(country=country)
        asset = Asset.objects.get(country=country)
        deposit_account = DepositBankAccountFactory.create(account__asset=asset)
        user_account = UserAccount.objects.for_customer(user, asset)
        op = Operation.objects.create_deposit(
            payment_method_account=deposit_account.account,
            user_account=user_account,
            amount=amount
        )
        op.hold()
        op.commit()
        return user

    return _user_with_balance


@pytest.mark.parametrize(
    'cryptocurrency,user_country',
    (
        ('BTC', 'AE'),
        ('BTC', 'SA'),
        ('BTC', 'BH'),
        ('BTC', 'KW'),
        ('BTC', 'OM'),

        ('ETH', 'AE'),
        ('ETH', 'SA'),
        ('ETH', 'BH'),
        ('ETH', 'KW'),
        ('ETH', 'OM'),

        ('XRP', 'AE'),
        ('XRP', 'SA'),
        ('XRP', 'BH'),
        ('XRP', 'KW'),
        ('XRP', 'OM'),

        ('LTC', 'AE'),
        ('LTC', 'SA'),
        ('LTC', 'BH'),
        ('LTC', 'KW'),
        ('LTC', 'OM'),

        ('BCH', 'AE'),
        ('BCH', 'SA'),
        ('BCH', 'BH'),
        ('BCH', 'KW'),
        ('BCH', 'OM'),

    )
)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_positive_order_buy(
    cryptocurrency,
    user_country,
    user_with_fiat_balance,
    client,
    offer_factory,
    settings,
):
    settings.LIVE_MARKET_TRADING = False

    base_amount = Decimal(1)
    quote_amount = Decimal(2)
    fee_amount = Decimal(1)

    user = user_with_fiat_balance(country=user_country, amount=100)
    client.force_login(user)

    pair = AssetPair.objects.get(base__symbol=cryptocurrency, quote__country=user_country)

    offer = offer_factory(
        asset_pair_id=pair.pk,
        action_type='buy',
        base_amount=base_amount,
        quote_amount=quote_amount,
        fee_amount=fee_amount
    )

    response = client.post('/order', {
        'token': offer.token
    })

    assert response.status_code == 200, response.content
    assert Decimal(response.data['data']['debitAmount']) == base_amount
    assert Decimal(response.data['data']['feeAmount']) == fee_amount
    assert Decimal(response.data['data']['creditAmount']) == quote_amount + fee_amount


@pytest.fixture
def user_with_crypto_balance(full_verified_user_factory):
    def _user_with_balance(country, asset, amount):
        user = full_verified_user_factory(country=country)
        deposit_account = DepositCryptoAccountFactory.create(account__asset=asset)
        user_account = UserAccount.objects.for_customer(user, asset)
        op = Operation.objects.create_deposit(
            payment_method_account=deposit_account.account,
            user_account=user_account,
            amount=amount
        )
        op.hold()
        op.commit()
        return user

    return _user_with_balance


@pytest.mark.parametrize(
    'cryptocurrency,user_country',
    (
        ('BTC', 'AE'),
        ('BTC', 'SA'),
        ('BTC', 'BH'),
        ('BTC', 'KW'),
        ('BTC', 'OM'),

        ('ETH', 'AE'),
        ('ETH', 'SA'),
        ('ETH', 'BH'),
        ('ETH', 'KW'),
        ('ETH', 'OM'),

        ('XRP', 'AE'),
        ('XRP', 'SA'),
        ('XRP', 'BH'),
        ('XRP', 'KW'),
        ('XRP', 'OM'),

        ('LTC', 'AE'),
        ('LTC', 'SA'),
        ('LTC', 'BH'),
        ('LTC', 'KW'),
        ('LTC', 'OM'),

        ('BCH', 'AE'),
        ('BCH', 'SA'),
        ('BCH', 'BH'),
        ('BCH', 'KW'),
        ('BCH', 'OM'),

    )
)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_positive_order_sell(
    cryptocurrency,
    user_country,
    user_with_crypto_balance,
    client,
    offer_factory,
    settings,
):
    settings.LIVE_MARKET_TRADING = False
    pair = AssetPair.objects.get(base__symbol=cryptocurrency, quote__country=user_country)

    base_amount = Decimal(1).quantize(Decimal(10) ** -pair.base_decimals)
    quote_amount = Decimal(1).quantize(Decimal(10) ** -pair.quote_decimals)
    fee_amount = Decimal(1).quantize(Decimal(10) ** -pair.quote_decimals)

    user = user_with_crypto_balance(country=user_country, amount=quote_amount + fee_amount, asset=pair.base)
    client.force_login(user)

    offer = offer_factory(
        asset_pair_id=pair.pk,
        action_type='sell',
        base_amount=base_amount,
        quote_amount=quote_amount,
        fee_amount=fee_amount,
    )

    response = client.post('/order', {
        'token': offer.token
    })

    assert response.status_code == 200, response.content
    assert Decimal(response.data['data']['debitAmount']) == quote_amount - \
           fee_amount
    assert Decimal(response.data['data']['feeAmount']) == fee_amount
    assert Decimal(response.data['data']['creditAmount']) == base_amount


@pytest.mark.urls('jibrel.exchanges.urls')
@pytest.mark.django_db
@given(offer=strategies.text())
def test_fuzzy_order(
    offer,
    full_verified_user,
    client,
    settings,
):
    settings.LIVE_MARKET_TRADING = False

    client.force_login(full_verified_user)

    response = client.post('/order', {
        'token': offer
    })

    assert response.status_code != 500, response.content


@pytest.mark.urls('jibrel.exchanges.urls')
@pytest.mark.django_db
def test_negative_sell_with_zero_balance(
    offer_factory,
    full_verified_user,
    client,
    settings,
):
    settings.LIVE_MARKET_TRADING = False

    client.force_login(full_verified_user)

    crypto = AssetFactory.create(type=Asset.CRYPTO)
    pair = AssetPair.objects.get(base=crypto, quote__country=full_verified_user.get_residency_country_code())

    offer = offer_factory(
        asset_pair_id=pair.pk,
        action_type='sell',
        base_amount=Decimal(1),
        quote_amount=Decimal(1),
        fee_amount=Decimal(1),
    )

    response = client.post('/order', {
        'token': offer.token
    })

    assert response.status_code != 200, response.content


@pytest.mark.django_db
def test_positive_exchange_operation_without_rate(
    offer_factory,
    user_with_crypto_balance,
    client,
    settings,
):
    settings.LIVE_MARKET_TRADING = False

    """Checks that old exchange operations without exchange rate handled safety"""

    user_country = 'AE'
    cryptocurrency = 'BTC'
    pair = AssetPair.objects.get(base__symbol=cryptocurrency, quote__country=user_country)

    base_amount = Decimal(1).quantize(Decimal(10) ** -pair.base_decimals)
    quote_amount = Decimal(1).quantize(Decimal(10) ** -pair.quote_decimals)
    fee_amount = Decimal(1).quantize(Decimal(10) ** -pair.quote_decimals)

    user = user_with_crypto_balance(country=user_country, amount=quote_amount + fee_amount, asset=pair.base)
    client.force_login(user)

    offer = offer_factory(
        asset_pair_id=pair.pk,
        action_type='sell',
        base_amount=base_amount,
        quote_amount=quote_amount,
        fee_amount=fee_amount,
    )

    response = client.post('/v1/exchanges/order', {
        'token': offer.token
    })

    assert response.status_code == 200
    operation_pk = response.data['data']['id']
    op = Operation.objects.get(pk=operation_pk)
    op.metadata = {}
    op.save()

    response = client.get(f'/v1/operations/{operation_pk}')

    assert response.status_code == 200
    assert response.data['data']['exchangeRate'] is None
