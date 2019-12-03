import functools
import time
from decimal import Decimal
from typing import Optional
from unittest import mock
from unittest.mock import PropertyMock
from uuid import UUID

import pytest

from jibrel.accounting.models import Asset
from jibrel.assets.models import AssetPair
from jibrel.authentication.models import User
from jibrel.exchanges.models import ActionType, Price
from jibrel.exchanges.repositories.price import PriceNotFoundException
from jibrel.exchanges.services.offering import offer_service
from jibrel.exchanges.services.trading import trading_service


def _get_one_price(
    pair_id: UUID,
    sell: Decimal,
    buy: Decimal,
    intermediate_crypto: Optional[Price] = None,
    intermediate_fiat: Optional[Price] = None,
):
    return Price(
        pair_id=pair_id,
        buy=buy,
        sell=sell,
        intermediate_crypto=intermediate_crypto,
        intermediate_fiat=intermediate_fiat,
        ts=int(time.time())
    )


def get_price(
    pair: AssetPair,
    buy_price: Decimal,
    sell_price: Decimal = None,
    intermediate_crypto_buy_price: Decimal = None,
    intermediate_crypto_sell_price: Decimal = None,
    intermediate_fiat_buy_price: Decimal = None,
    intermediate_fiat_sell_price: Decimal = None,
):
    if sell_price is None:
        sell_price = buy_price

    if intermediate_crypto_buy_price is not None and intermediate_crypto_sell_price is None:
        intermediate_crypto_sell_price = intermediate_crypto_buy_price

    if intermediate_fiat_buy_price is not None and intermediate_fiat_sell_price is None:
        intermediate_fiat_sell_price = intermediate_fiat_buy_price

    intermediate_crypto = None
    intermediate_fiat = None

    if pair.intermediate_pairs.exists():
        assert intermediate_fiat_buy_price is not None and intermediate_crypto_buy_price is not None
        intermediate_crypto = _get_one_price(
            pair_id=pair.intermediate_pairs.crypto().get().pk,
            buy=intermediate_fiat_buy_price,
            sell=intermediate_crypto_sell_price,
        )
        intermediate_fiat = _get_one_price(
            pair_id=pair.intermediate_pairs.fiat().get().pk,
            buy=intermediate_fiat_buy_price,
            sell=intermediate_fiat_sell_price,
        )
    return _get_one_price(
        pair_id=pair.pk,
        buy=buy_price,
        sell=sell_price,
        intermediate_fiat=intermediate_fiat,
        intermediate_crypto=intermediate_crypto,
    )


def _get_by_pairs_mock_helper(prices, *ids):
    return [prices[id] for id in ids]


def _get_by_pair_id_mock_helper(prices, id):
    try:
        return prices[id]
    except KeyError:
        raise PriceNotFoundException


@pytest.fixture()
def set_price(mocker):
    prices = {}

    get_by_pairs = functools.partial(_get_by_pairs_mock_helper, prices)
    get_by_pair_id = functools.partial(_get_by_pair_id_mock_helper, prices)

    mocker.patch('jibrel.exchanges.repositories.price.price_repository.get_by_pairs', get_by_pairs)
    mocker.patch('jibrel.exchanges.repositories.price.price_repository.get_by_pair_id', get_by_pair_id)

    def _set_price(
        pair: AssetPair,
        buy_price: Decimal,
        sell_price: Decimal = None,
        intermediate_crypto_buy_price: Decimal = None,
        intermediate_crypto_sell_price: Decimal = None,
        intermediate_fiat_buy_price: Decimal = None,
        intermediate_fiat_sell_price: Decimal = None,
    ):
        if intermediate_crypto_buy_price is None:
            intermediate_crypto_buy_price = buy_price
        if intermediate_fiat_buy_price is None:
            intermediate_fiat_buy_price = buy_price

        price = get_price(
            pair=pair,
            buy_price=buy_price,
            sell_price=sell_price,
            intermediate_crypto_buy_price=intermediate_crypto_buy_price,
            intermediate_crypto_sell_price=intermediate_crypto_sell_price,
            intermediate_fiat_buy_price=intermediate_fiat_buy_price,
            intermediate_fiat_sell_price=intermediate_fiat_sell_price,
        )
        prices[price.pair_id] = price
        return price

    return _set_price


@pytest.fixture()
def create_offer(db, mocker):
    def _create_offer(
        user_id: UUID,
        pair: AssetPair,
        price: Price,
        action_type: ActionType,
        base_amount: Optional[Decimal] = None,
        quote_amount: Optional[Decimal] = None,
        fee: Decimal = Decimal(0),
        validate_limits: bool = False,
    ):
        mocker.patch.object(offer_service, 'get_price', return_value=price)
        mocker.patch.object(pair, 'buy_fee', new_callable=PropertyMock(return_value=fee, spec=fee))
        mocker.patch.object(pair, 'sell_fee', new_callable=PropertyMock(return_value=fee, spec=fee))
        if not validate_limits:
            mocker.patch('jibrel.exchanges.services.offering.OfferBuilder.validate_by_limits')
        return offer_service.create(
            user_id=user_id,
            asset_pair=pair,
            action_type=action_type,
            base_amount=base_amount,
            quote_amount=quote_amount,
        )

    return _create_offer


@pytest.fixture()
def create_exchange_operation(db, create_offer, settings, mocker):
    def _create_exchange_operation(
        *,
        user: User,
        action_type: ActionType,
        crypto_asset: Asset,
        fiat_asset: Asset,
        crypto_amount: Optional[Decimal] = None,
        fiat_amount: Optional[Decimal] = None,
        crypto_to_intermediate_price: Decimal,
        intermediate_to_fiat_price: Decimal,
        fee: Decimal = Decimal(0),
        commit: bool = True,
        create_market_order: bool = True
    ):
        mocker.patch('jibrel.exchanges.tasks.add_order.delay')
        if create_market_order:
            settings.LIVE_MARKET_TRADING = True
        pair = AssetPair.objects.get(base=crypto_asset, quote=fiat_asset)
        price = get_price(
            pair=pair,
            buy_price=crypto_to_intermediate_price * intermediate_to_fiat_price,
            intermediate_crypto_buy_price=crypto_to_intermediate_price,
            intermediate_fiat_buy_price=intermediate_to_fiat_price,
        )
        offer = create_offer(
            user_id=user.pk,
            pair=pair,
            price=price,
            action_type=action_type,
            base_amount=crypto_amount,
            quote_amount=fiat_amount,
            fee=fee,
        )
        with mock.patch.object(trading_service, 'get_offer_by_token', return_value=offer):
            operation = trading_service.place_order(user, offer.token)
        if commit:
            operation.commit()
        return operation

    return _create_exchange_operation


@pytest.fixture()
def create_prepared_exchange_operation(create_deposit_operation, create_exchange_operation):
    def _create_prepared_exchange_operation(
        *,
        user,
        action_type,
        crypto_asset,
        fiat_asset,
        crypto_to_intermediate_price,
        intermediate_to_fiat_price,
        crypto_amount=None,
        fiat_amount=None,
        fee=Decimal(0),
        commit=True,
    ):
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
            amount=amount_to_deposit,
        )

        return create_exchange_operation(
            user=user,
            action_type=action_type,
            crypto_asset=crypto_asset,
            fiat_asset=fiat_asset,
            crypto_amount=crypto_amount,
            crypto_to_intermediate_price=crypto_to_intermediate_price,
            intermediate_to_fiat_price=intermediate_to_fiat_price,
            fee=fee,
            commit=commit,
        )

    return _create_prepared_exchange_operation
