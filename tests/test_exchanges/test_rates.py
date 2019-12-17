from decimal import (
    ROUND_DOWN,
    Decimal
)

import pytest

from jibrel.assets import AssetPair


def _quantize(value: Decimal, decimals: int):
    return value.quantize(
        Decimal('.1') ** decimals,
        rounding=ROUND_DOWN
    )


@pytest.mark.parametrize('currency', ('AED', 'SAR', 'BHD', 'KWD', 'OMR', 'USD'))
@pytest.mark.django_db
@pytest.mark.urls('jibrel.exchanges.urls')
def test_currency(currency, client, set_price):
    pairs = AssetPair.objects.filter(
        quote__symbol__iexact=currency
    ).select_related('base', 'quote')

    sell_price = Decimal(9)
    buy_price = Decimal(11)
    results = {}

    for pair in pairs:
        buy = _quantize(buy_price, pair.quote.decimals)
        sell = _quantize(sell_price, pair.quote.decimals)
        set_price(
            pair,
            buy_price=buy,
            sell_price=sell,
            intermediate_crypto_buy_price=buy_price,
            intermediate_fiat_buy_price=sell_price,
        )
        results[str(pair.base)] = {
            'buy': buy,
            'sell': sell
        }

    response = client.get('/rates', {'quote': currency})
    assert response.status_code == 200

    for data in response.data['data'].values():
        for key in ('buy', 'sell',):
            assert data[key] == str(results[data['base']][key])
