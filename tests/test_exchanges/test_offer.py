import itertools
from decimal import Decimal
from typing import (
    NamedTuple,
    Optional,
    Union
)

import pytest
from hypothesis import (
    given,
    settings,
    strategies
)
from rest_framework.test import APIClient

from jibrel.accounting import Asset
from django_banking.tests.factories.factories import AssetFactory
from jibrel.assets import (
    AssetPair,
    AssetPairFactory
)
from jibrel.exchanges import PriceNotFoundException


@pytest.fixture
def client():
    client = APIClient()

    return client


PARAMETRIZE_ARGS = (
    'action,cryptocurrency,user_country',
    (
        ('buy', 'BTC', 'AE'),
        ('buy', 'BTC', 'SA'),
        ('buy', 'BTC', 'BH'),
        ('buy', 'BTC', 'KW'),
        ('buy', 'BTC', 'OM'),
        ('sell', 'BTC', 'AE'),
        ('sell', 'BTC', 'SA'),
        ('sell', 'BTC', 'BH'),
        ('sell', 'BTC', 'KW'),
        ('sell', 'BTC', 'OM'),

        ('buy', 'ETH', 'AE'),
        ('buy', 'ETH', 'SA'),
        ('buy', 'ETH', 'BH'),
        ('buy', 'ETH', 'KW'),
        ('buy', 'ETH', 'OM'),
        ('sell', 'ETH', 'AE'),
        ('sell', 'ETH', 'SA'),
        ('sell', 'ETH', 'BH'),
        ('sell', 'ETH', 'KW'),
        ('sell', 'ETH', 'OM'),

        ('buy', 'XRP', 'AE'),
        ('buy', 'XRP', 'SA'),
        ('buy', 'XRP', 'BH'),
        ('buy', 'XRP', 'KW'),
        ('buy', 'XRP', 'OM'),
        ('sell', 'XRP', 'AE'),
        ('sell', 'XRP', 'SA'),
        ('sell', 'XRP', 'BH'),
        ('sell', 'XRP', 'KW'),
        ('sell', 'XRP', 'OM'),

        ('buy', 'LTC', 'AE'),
        ('buy', 'LTC', 'SA'),
        ('buy', 'LTC', 'BH'),
        ('buy', 'LTC', 'KW'),
        ('buy', 'LTC', 'OM'),
        ('sell', 'LTC', 'AE'),
        ('sell', 'LTC', 'SA'),
        ('sell', 'LTC', 'BH'),
        ('sell', 'LTC', 'KW'),
        ('sell', 'LTC', 'OM'),

        ('buy', 'BCH', 'AE'),
        ('buy', 'BCH', 'SA'),
        ('buy', 'BCH', 'BH'),
        ('buy', 'BCH', 'KW'),
        ('buy', 'BCH', 'OM'),
        ('sell', 'BCH', 'AE'),
        ('sell', 'BCH', 'SA'),
        ('sell', 'BCH', 'BH'),
        ('sell', 'BCH', 'KW'),
        ('sell', 'BCH', 'OM'),
    )
)


class GetOfferParametrizeArg(NamedTuple):
    id: str
    base_amount: Optional[Decimal]
    base_top_limit: Decimal
    base_bottom_limit: Decimal
    quote_amount: Optional[Decimal]
    quote_top_limit: Decimal
    quote_bottom_limit: Decimal
    price: Decimal
    expected_code: int


args = [
    GetOfferParametrizeArg(
        id='base min',
        base_amount=Decimal(1),
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(1),
        quote_amount=None,
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=200,
    ),
    GetOfferParametrizeArg(
        id='base max',
        base_amount=Decimal(100),
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(1),
        quote_amount=None,
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=200,
    ),
    GetOfferParametrizeArg(
        id='quote min',
        base_amount=None,
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(1),
        quote_amount=Decimal(1)  # in this case for buy fee will be excluded from quote_amount and we broke limit
                     + Decimal('0.1'),
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(1),
        price=Decimal(1),

        expected_code=200,
    ),
    GetOfferParametrizeArg(
        id='quote max',
        base_amount=None,
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(1),
        quote_amount=Decimal(100),
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=200,
    ),
    GetOfferParametrizeArg(
        id='base lesser min',
        base_amount=Decimal(1),
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(2),
        quote_amount=None,
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=400,
    ),
    GetOfferParametrizeArg(
        id='base bigger max',
        base_amount=Decimal(101),
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(2),
        quote_amount=None,
        quote_top_limit=Decimal(10000),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=400,
    ),
    GetOfferParametrizeArg(
        id='quote lesser min',
        base_amount=None,
        base_top_limit=Decimal(100),
        base_bottom_limit=Decimal(0),
        quote_amount=Decimal(1),
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(2),
        price=Decimal(1),

        expected_code=400,
    ),
    GetOfferParametrizeArg(
        id='quote bigger max',
        base_amount=None,
        base_top_limit=Decimal(10000),
        base_bottom_limit=Decimal(0),
        quote_amount=Decimal(102),
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(2),
        price=Decimal(1),

        expected_code=400,
    ),
    GetOfferParametrizeArg(
        id='base big precision',
        base_amount=Decimal('.1') ** 10,
        base_top_limit=Decimal(10000),
        base_bottom_limit=Decimal(0),
        quote_amount=Decimal(101),
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=400,
    ),
    GetOfferParametrizeArg(
        id='quote big precision',
        base_amount=None,
        base_top_limit=Decimal(10000),
        base_bottom_limit=Decimal(0),
        quote_amount=Decimal('.1') ** 10,
        quote_top_limit=Decimal(100),
        quote_bottom_limit=Decimal(0),
        price=Decimal(1),

        expected_code=400,
    ),

]


@pytest.mark.parametrize(
    'action,base_amount,base_top_limit,base_bottom_limit,quote_amount' +
    ',quote_top_limit,quote_bottom_limit,price,expected_code',
    ((action, *arg[1:]) for action, arg in itertools.product(('sell', 'buy'), args)),
    ids=[f'{action} {arg.id}' for action, arg in itertools.product(('sell', 'buy'), args)]
)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_get_offer(
    action,
    base_amount,
    base_top_limit,
    base_bottom_limit,
    quote_amount,
    quote_top_limit,
    quote_bottom_limit,
    price,
    expected_code,

    set_price,
    full_verified_user,
    client: APIClient,
):
    client.force_login(full_verified_user)

    base_asset = AssetFactory.create(type=Asset.CRYPTO)
    quote_asset = Asset.objects.get(type=Asset.FIAT, country=full_verified_user.get_residency_country_code())
    pair = AssetPairFactory.create(
        base=base_asset,
        quote=quote_asset,
        base_top_limit=base_top_limit,
        base_bottom_limit=base_bottom_limit,
        quote_top_limit=quote_top_limit,
        quote_bottom_limit=quote_bottom_limit,
    )
    intermediate_asset = Asset.objects.create(type=Asset.FIAT)

    intermediate_crypto = AssetPairFactory.create(
        base=base_asset,
        quote=intermediate_asset,
        base_top_limit=base_top_limit,
        base_bottom_limit=base_bottom_limit,
        quote_top_limit=quote_top_limit,
        quote_bottom_limit=quote_bottom_limit,
    )

    intermediate_fiat = AssetPairFactory.create(
        base=intermediate_asset,
        quote=quote_asset,
        base_top_limit=base_top_limit,
        base_bottom_limit=base_bottom_limit,
        quote_top_limit=quote_top_limit,
        quote_bottom_limit=quote_bottom_limit,
    )

    pair.intermediate_pairs.add(intermediate_crypto, intermediate_fiat)

    set_price(pair, price, intermediate_crypto_buy_price=price, intermediate_fiat_buy_price=price)

    request_data = {
        'actionType': action,
        'assetPairId': str(pair.uuid),
    }
    if base_amount is not None:
        request_data['baseAmount'] = base_amount
    elif quote_amount is not None:
        request_data['quoteAmount'] = quote_amount

    response = client.post('/offer', request_data)

    assert response.status_code == expected_code, response.content


@pytest.mark.parametrize(*PARAMETRIZE_ARGS)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_negative_price_not_found_turns_off_trade(
    action,
    cryptocurrency,
    user_country,
    full_verified_user_factory,
    client: APIClient,
    mocker,
):
    user = full_verified_user_factory(country=user_country)
    client.force_login(user)

    asset_to_buy = Asset.objects.get(symbol=cryptocurrency)
    pair = AssetPair.objects.get(base=asset_to_buy, quote__country=user.get_residency_country_code())

    mocker.patch('jibrel.exchanges.services.offering.OfferService.get_price', side_effect=PriceNotFoundException)
    mocked = mocker.patch('jibrel.exchanges.views.disable_trading')
    response = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response.status_code == 503
    mocked.assert_called()


@pytest.mark.parametrize(*PARAMETRIZE_ARGS)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_positive_same_price(
    action,
    cryptocurrency,
    user_country,
    full_verified_user_factory,
    client: APIClient,
    set_price,
):
    user = full_verified_user_factory(country=user_country)
    client.force_login(user)

    base = Asset.objects.get(symbol=cryptocurrency)
    quote = Asset.objects.get(country=user.get_residency_country_code())
    pair = AssetPair.objects.get(base=base, quote=quote)

    price = pair.quote_bottom_limit / pair.base_bottom_limit + Decimal(1)
    set_price(pair, price, intermediate_crypto_buy_price=price, intermediate_fiat_buy_price=price)

    response1 = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response1.status_code == 200, response1.content

    response2 = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response2.status_code == 200, response2.content

    assert response1.data['data']['price'] == response2.data['data']['price']


@pytest.mark.parametrize(*PARAMETRIZE_ARGS)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_positive_different_price(
    action,
    cryptocurrency,
    user_country,
    full_verified_user_factory,
    client: APIClient,
    mocker,
    set_price,
):
    mocker.patch('jibrel.exchanges.repositories.price.price_repository._price_for_user_lifetime', 0)
    user = full_verified_user_factory(country=user_country)
    client.force_login(user)

    asset_to_buy = Asset.objects.get(symbol=cryptocurrency)
    pair = AssetPair.objects.get(base=asset_to_buy, quote__country=user.get_residency_country_code())

    price = pair.quote_bottom_limit / pair.base_bottom_limit + Decimal(1)
    set_price(pair, price)

    response1 = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response1.status_code == 200, response1.content

    price += Decimal(1)
    set_price(pair, price)

    response2 = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response2.status_code == 200, response2.content

    assert response1.data['data']['price'] != response2.data['data']['price']


@pytest.mark.parametrize(*PARAMETRIZE_ARGS)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_positive_token_is_not_expired(
    action,
    cryptocurrency,
    user_country,
    full_verified_user_factory,
    client: APIClient,
    settings,
    set_price,
):
    settings.EXCHANGE_OFFER_LIFETIME = 1000
    user = full_verified_user_factory(country=user_country)
    client.force_login(user)

    asset_to_buy = Asset.objects.get(symbol=cryptocurrency)
    pair = AssetPair.objects.get(base=asset_to_buy, quote__country=user.get_residency_country_code())
    set_price(pair, pair.quote_bottom_limit / pair.base_bottom_limit + Decimal(1))
    response = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit * 2
    })

    assert response.status_code == 200, response.content

    response = client.post('/order', {
        'token': response.data['data']['token']
    })

    assert response.status_code != 400, response.content


@pytest.mark.parametrize(*PARAMETRIZE_ARGS)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_negative_token_expired(
    action,
    cryptocurrency,
    user_country,
    full_verified_user_factory,
    client: APIClient,
    mocker,
    set_price,
):
    mocker.patch('jibrel.exchanges.repositories.offer.offer_repository._offer_lifetime', 0)
    user = full_verified_user_factory(country=user_country)
    client.force_login(user)

    asset_to_buy = Asset.objects.get(symbol=cryptocurrency)
    pair = AssetPair.objects.get(base=asset_to_buy, quote__country=user.get_residency_country_code())
    set_price(pair, pair.quote_bottom_limit / pair.base_bottom_limit + Decimal(1))
    assert pair.base_bottom_limit != 0, f'{pair.uuid}: {pair.get_symbol()}'
    response = client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response.status_code == 200, response.content

    response = client.post('/order', {
        'token': response.data['data']['token']
    })

    assert response.status_code == 400, response.content


@pytest.fixture
def pair(db):
    base_asset= AssetFactory.create(type=Asset.CRYPTO, country='')
    quote_asset = AssetFactory.create(type=Asset.FIAT, country='AE')

    intermediate_asset = AssetFactory.create(type=Asset.FIAT)

    pair = AssetPair.objects.get(base=base_asset, quote=quote_asset)

    intermediate_crypto = AssetPairFactory.create(
        base=base_asset,
        quote=intermediate_asset,
    )

    intermediate_fiat = AssetPairFactory.create(
        base=intermediate_asset,
        quote=quote_asset,
    )

    pair.intermediate_pairs.add(intermediate_crypto, intermediate_fiat)
    return pair


@pytest.mark.parametrize(
    'action,amount_type',
    (
        ('buy', 'base'),
        ('buy', 'quote'),
        ('sell', 'base'),
        ('sell', 'quote'),
    )
)
@pytest.mark.django_db(transaction=True)
@pytest.mark.urls('jibrel.exchanges.urls')
@given(amount=strategies.decimals())
@settings(deadline=None)
def test_fuzzy_get_offer(
    amount,
    action,
    amount_type,
    full_verified_user_factory,
    client: APIClient,
    pair,
    set_price,
):
    user = full_verified_user_factory(country=pair.quote.country)
    client.force_login(user)

    set_price(pair, Decimal(1), intermediate_fiat_buy_price=Decimal(1), intermediate_crypto_buy_price=Decimal(1))

    client.post('/offer', {
        'actionType': action,
        'assetPairId': str(pair.uuid),
        f'{amount_type}Amount': amount
    })


class ParametrizeArg(NamedTuple):
    action_type: str
    base_amount: Union[Decimal, None]
    quote_amount: Union[Decimal, None]
    buy_price: Decimal
    sell_price: Decimal
    buy_fee: Decimal
    sell_fee: Decimal
    expected_base_amount: Decimal
    expected_quote_amount: Decimal
    expected_fee_amount: Decimal
    expected_total_amount: Decimal


args = (
    ParametrizeArg(
        action_type='buy',
        base_amount=Decimal('0.5'),
        quote_amount=None,
        buy_price=Decimal('36773.40'),
        sell_price=Decimal('36526.80'),
        buy_fee=Decimal('0.0075'),
        sell_fee=Decimal('0.01'),
        expected_base_amount=Decimal('0.5'),
        expected_quote_amount=Decimal('18386.70'),
        expected_fee_amount=Decimal('137.90'),
        expected_total_amount=Decimal('18524.60')
    ),
    ParametrizeArg(
        action_type='buy',
        base_amount=None,
        quote_amount=Decimal('18524.60'),
        buy_price=Decimal('36773.40'),
        sell_price=Decimal('36526.80'),
        buy_fee=Decimal('0.0075'),
        sell_fee=Decimal('0.01'),
        expected_base_amount=Decimal('0.5'),
        expected_quote_amount=Decimal('18524.60'),
        expected_fee_amount=Decimal('137.90'),
        expected_total_amount=Decimal('18524.60')
    ),
    ParametrizeArg(
        action_type='sell',
        base_amount=Decimal('0.5'),
        quote_amount=None,
        buy_price=Decimal('36773.40'),
        sell_price=Decimal('36526.80'),
        buy_fee=Decimal('0.0075'),
        sell_fee=Decimal('0.01'),
        expected_base_amount=Decimal('0.5'),
        expected_quote_amount=Decimal('18263.40'),
        expected_fee_amount=Decimal('182.63'),
        expected_total_amount=Decimal('18080.77')
    ),
    ParametrizeArg(
        action_type='sell',
        base_amount=None,
        quote_amount=Decimal('18263.40'),
        buy_price=Decimal('36773.40'),
        sell_price=Decimal('36526.80'),
        buy_fee=Decimal('0.0075'),
        sell_fee=Decimal('0.01'),
        expected_base_amount=Decimal('0.5'),
        expected_quote_amount=Decimal('18263.40'),
        expected_fee_amount=Decimal('182.63'),
        expected_total_amount=Decimal('18080.77')
    ),
)


@pytest.mark.parametrize(
    'action_type,base_amount,quote_amount,buy_price,sell_price,buy_fee,' +
    'sell_fee,expected_base_amount,expected_quote_amount,expected_fee_amount,expected_total_amount',
    args,
)
@pytest.mark.urls('jibrel.exchanges.urls')
@pytest.mark.django_db
def test_offer_logic(
    action_type,
    base_amount,
    quote_amount,
    buy_price,
    sell_price,
    buy_fee,
    sell_fee,
    expected_base_amount,
    expected_quote_amount,
    expected_fee_amount,
    expected_total_amount,
    client: APIClient,
    full_verified_user,
    set_price,
):
    client.force_login(full_verified_user)
    base_asset = AssetFactory.create(decimals=6, type=Asset.CRYPTO)
    quote_asset = AssetFactory.create(
        decimals=2, country=full_verified_user.get_residency_country_code(), type=Asset.FIAT
    )
    pair = AssetPairFactory.create(
        base=base_asset,
        quote=quote_asset,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        base_top_limit=10 ** 6,
        base_bottom_limit=0,
        quote_top_limit=10 ** 6,
        quote_bottom_limit=0,
    )

    intermediate_asset = Asset.objects.create(type=Asset.FIAT)

    intermediate_crypto = AssetPairFactory.create(
        base=base_asset,
        quote=intermediate_asset,
    )

    intermediate_fiat = AssetPairFactory.create(
        base=intermediate_asset,
        quote=quote_asset,
    )

    pair.intermediate_pairs.add(intermediate_crypto, intermediate_fiat)

    set_price(pair, buy_price=buy_price, sell_price=sell_price)

    request_data = {
        'actionType': action_type,
        'assetPairId': str(pair.uuid),
    }
    if base_amount is not None:
        request_data['baseAmount'] = str(base_amount)
    if quote_amount is not None:
        request_data['quoteAmount'] = str(quote_amount)

    response = client.post('/offer', request_data)

    assert response.status_code == 200, response.content
    assert Decimal(response.data['data']['price']) == buy_price if action_type == 'buy' else sell_price
    assert Decimal(response.data['data']['baseAmount']) == expected_base_amount
    assert Decimal(response.data['data']['quoteAmount']) == expected_quote_amount
    assert Decimal(response.data['data']['feeAmount']) == expected_fee_amount
    assert Decimal(response.data['data']['totalAmount']) == expected_total_amount


INTERMEDIATE_PAIRS = {
    'f1748578-6e00-4804-a403-08a3ea6f4533',  # USD/AED
    'db432e7b-2f4a-4fe8-995f-531cefc9ec7a',  # USD/SAR
    '3672af5e-bae7-4564-9390-d66a5de1f805',  # USD/BHD
    '4e0bb199-e20e-481d-907e-96b812b06612',  # USD/KWD
    '220a4374-6273-49d0-85e0-b7339f26ec99',  # USD/OMR
    '8089ec24-da51-481a-abcc-504ad0362020',  # BTC/USD
    'e702619b-f046-4eba-8fb0-38786ccd9eef',  # ETH/USD
    '9f3ef7dd-57bf-471c-9c77-ef59bcbb51ea',  # XRP/USD
    '8cdfb571-de37-4a16-a2e8-338ecb1b8b06',  # LTC/USD
    '657f8294-3242-43c4-a204-e8eff0f2ae0b',  # BCH/USD
}

AE_PAIRS = {
    '74c52de5-025d-45db-9c2c-8328e97aeacd',  # BTC/AED
    'd7393618-73ff-4602-ac29-435908f9bfa9',  # ETH/AED
    'e4a6aa1a-42be-4a47-ba68-a4e5e03b11ec',  # XRP/AED
    '4ba1ef8c-2443-4c60-8520-e258f256c946',  # LTC/AED
    '718158b5-aa34-458e-b7f4-0ebc5a2306c0',  # BCH/AED
}

BH_PAIRS = {
    '442f10ef-7a18-4d72-8e9e-061c641efa5f',  # BTC/BHD
    'c753d063-ed0e-4aee-9eac-8366db6c1f98',  # ETH/BHD
    'bc3f5585-b8ff-4f62-b436-ed992a719c84',  # XRP/BHD
    '4ba1e43a-fd6e-4767-8420-5cf38bf9bd1e',  # LTC/BHD
    '067b1689-b7a7-427c-8b7f-9278c50270cf',  # BCH/BHD
}

SA_PAIRS = {
    '835907de-4289-44d7-9285-e2a75d2a27c4',  # BTC/SAR
    '6f46d353-f024-43d2-9398-9716a69ea271',  # ETH/SAR
    '177734f6-0462-486f-adab-92b3d0b224fd',  # XRP/SAR
    '1ef701b9-39b5-4e1e-ad30-4b3fb9854a2a',  # LTC/SAR
    '929e4fe8-9732-4b30-bd55-5eab0c6dd027',  # BCH/SAR
}

KW_PAIRS = {
    '6bf3a5e3-3520-432a-ad16-6afe8026dbc3',  # BTC/KWD
    'fd76ca82-db48-43be-beca-b03569d5acd6',  # ETH/KWD
    'aeafe53e-ce92-4931-9a0f-61b05d3f06f9',  # XRP/KWD
    'c1639412-2bc0-48ad-ae20-487f68ecf3e0',  # LTC/KWD
    '54df332d-7818-40d8-8376-e750bdc38928',  # BCH/KWD
}

OM_PAIRS = {
    '9ad0279c-9cbe-49a4-a1b3-090432f892c0',  # BTC/OMR
    'a7398e4b-3e62-46f0-8f6b-77fcc49e0103',  # ETH/OMR
    'b425333f-1be3-4d5f-9660-108f74adf2f0',  # XRP/OMR
    'cbe4669a-fe12-486e-a0b2-4dbe88b5332d',  # LTC/OMR
    'e353d1c9-c308-44a8-8bfd-6c31cebf304e',  # BCH/OMR
}

COUNTRY_TO_PAIRS = {
    'AE': AE_PAIRS,
    'BH': BH_PAIRS,
    'SA': SA_PAIRS,
    'KW': KW_PAIRS,
    'OM': OM_PAIRS,
}


def params_for_country(country):
    params = []
    for cn, pairs in COUNTRY_TO_PAIRS.items():
        marks = []
        if cn == country:
            marks.append(pytest.mark.xfail(strict=True))
        for pair in pairs:
            params.append(pytest.param(country, pair, marks=marks))
    params.extend(
        (country, p) for p in INTERMEDIATE_PAIRS
    )
    return params


@pytest.mark.parametrize(
    'country,pair',
    (
        *params_for_country('AE'),
        *params_for_country('BH'),
        *params_for_country('SA'),
        *params_for_country('KW'),
        *params_for_country('OM'),
    )
)
@pytest.mark.urls('jibrel.exchanges.urls')
@pytest.mark.django_db
def test_negative_wrong_pair(
    country,
    pair,
    client,
    full_verified_user_factory,
    set_price,
):
    user = full_verified_user_factory(country)
    client.force_login(user)
    pair = AssetPair.objects.get(pk=pair)
    set_price(pair, pair.quote_bottom_limit / (pair.base_bottom_limit or Decimal(1)) + Decimal(1))

    response = client.post('/offer', {
        'actionType': 'sell',
        'assetPairId': str(pair.uuid),
        'baseAmount': pair.base_bottom_limit
    })

    assert response.status_code == 400, response.content


@pytest.mark.parametrize(
    'action,base_amount,quote_amount,base_asset_symbol',
    (
        ('sell', Decimal(0), None, 'BTC'),
        ('sell', Decimal(0), None, 'ETH'),
        ('sell', Decimal(0), None, 'XRP'),
        ('sell', Decimal(0), None, 'LTC'),
        ('sell', Decimal(0), None, 'BCH'),

        ('sell', None, Decimal(0), 'BTC'),
        ('sell', None, Decimal(0), 'ETH'),
        ('sell', None, Decimal(0), 'XRP'),
        ('sell', None, Decimal(0), 'LTC'),
        ('sell', None, Decimal(0), 'BCH'),

        ('buy', Decimal(0), None, 'BTC'),
        ('buy', Decimal(0), None, 'ETH'),
        ('buy', Decimal(0), None, 'XRP'),
        ('buy', Decimal(0), None, 'LTC'),
        ('buy', Decimal(0), None, 'BCH'),

        ('buy', None, Decimal(0), 'BTC'),
        ('buy', None, Decimal(0), 'ETH'),
        ('buy', None, Decimal(0), 'XRP'),
        ('buy', None, Decimal(0), 'LTC'),
        ('buy', None, Decimal(0), 'BCH'),
    )
)
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_negative_zero_amount(
    action,
    base_amount,
    quote_amount,
    base_asset_symbol,
    full_verified_user,
    client: APIClient,
    set_price,
):
    client.force_login(full_verified_user)

    base_asset = Asset.objects.get(symbol=base_asset_symbol)
    pair = AssetPair.objects.get(base=base_asset, quote__country=full_verified_user.get_residency_country_code())
    set_price(pair, pair.quote_bottom_limit / pair.base_bottom_limit + Decimal(1))
    request_data = {
        'actionType': action,
        'assetPairId': str(pair.uuid),
    }
    if base_amount is not None:
        request_data['baseAmount'] = str(base_amount)
    elif quote_amount is not None:
        request_data['quoteAmount'] = str(quote_amount)
    else:
        raise ValueError()
    response = client.post('/offer', request_data)

    assert response.status_code == 400, response.content
