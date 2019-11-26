import pytest

from jibrel.exchanges.exceptions import (
    InactiveTradingException,
    MarketException
)
from jibrel.exchanges.tasks import (
    update_crypto_prices_task,
    update_fiat_prices_task,
    update_prices_task
)
from jibrel.exchanges import PriceNotFoundException


@pytest.mark.parametrize(
    'exc',
    (
        MarketException,
        Exception,
        pytest.param(InactiveTradingException, marks=pytest.mark.xfail(strict=True)),
    )
)
@pytest.mark.django_db
def test_update_fiat_prices_task_turns_trading_off(mocker, exc):
    mocker.patch('jibrel.exchanges.tasks.price_repository')
    mocker.patch('jibrel.exchanges.tasks.fiat_price_calculator', side_effect=exc)
    mocked = mocker.patch('jibrel.exchanges.tasks.disable_trading')
    update_fiat_prices_task.apply()
    mocked.assert_called()


@pytest.mark.parametrize(
    'exc',
    (
        MarketException,
        Exception,
        pytest.param(InactiveTradingException, marks=pytest.mark.xfail(strict=True)),
    )
)
@pytest.mark.django_db
def test_update_crypto_prices_task_turns_trading_off(mocker, exc):
    mocker.patch('jibrel.exchanges.tasks.price_repository')
    mocker.patch('jibrel.exchanges.tasks.crypto_price_calculator', side_effect=exc)
    mocked = mocker.patch('jibrel.exchanges.tasks.disable_trading')
    update_crypto_prices_task.apply()
    mocked.assert_called()


@pytest.mark.parametrize(
    'exc',
    (
        PriceNotFoundException,
        MarketException,
        Exception,
        pytest.param(InactiveTradingException, marks=pytest.mark.xfail(strict=True)),
    )
)
@pytest.mark.django_db
def test_update_prices_task_turns_trading_off(mocker, exc):
    mocker.patch('jibrel.exchanges.tasks.price_repository.get_by_pair_id', side_effect=exc)
    mocked = mocker.patch('jibrel.exchanges.tasks.disable_trading')
    update_prices_task.apply()
    mocked.assert_called()
