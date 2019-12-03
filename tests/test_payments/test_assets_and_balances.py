from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from jibrel.accounting import Asset, Operation
from jibrel.accounting.factories import AccountFactory
from jibrel.assets import AssetPair
from jibrel.authentication.factories import VerifiedUser
from jibrel.payments.models import UserAccount

from .utils import validate_response_schema


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.mark.django_db
def test_assets_list(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.get('/v1/assets/')
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)
    assert len(resp.data) == Asset.objects.all().count()
    validate_response_schema('/v1/assets', 'GET', resp)


@pytest.mark.django_db
def test_balance(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.get('/v1/balance/')
    validate_response_schema('/v1/balance', 'GET', resp)
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)
    assert len(resp.data) == Asset.objects.filter(type=Asset.CRYPTO).count() + 1


@pytest.mark.django_db
def test_balance_wrong_quote(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.get('/v1/balance/?quote=asd')

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_balance_with_transactions(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    any_crypto = Asset.objects.filter(type=Asset.CRYPTO).first()
    user_account = UserAccount.objects.for_customer(user, any_crypto)
    payment_method_account = AccountFactory.create(asset=any_crypto)

    Operation.objects.create_deposit(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('100.00')
    ).commit()

    Operation.objects.create_deposit(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('10.00')
    ).commit()

    resp = client.get('/v1/balance/')
    validate_response_schema('/v1/balance', 'GET', resp)
    for account in resp.data:
        if account['assetId'] == str(any_crypto.uuid):
            assert Decimal(account['balance']) == Decimal('110.000000')
            break
    else:
        pytest.fail("No required asset found")


@pytest.mark.django_db
def test_totalfiat_balance(set_price):
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)
    any_crypto = Asset.objects.filter(type=Asset.CRYPTO).first()
    user_account = UserAccount.objects.for_customer(user, any_crypto)
    payment_method_account = AccountFactory.create(asset=any_crypto)

    user_country_code = user.get_residency_country_code()
    user_currency = Asset.objects.get(country=user_country_code)

    pair = AssetPair.objects.get(base=any_crypto, quote=user_currency)
    set_price(
        pair, Decimal('2.0'), Decimal('2.0'),
        intermediate_crypto_buy_price=Decimal('2.0'),
        intermediate_fiat_buy_price=Decimal('2.0')
    )

    Operation.objects.create_deposit(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('100.00')
    ).commit()

    Operation.objects.create_deposit(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('10.00')
    ).commit()

    resp = client.get('/v1/balance/')

    assert resp.status_code == status.HTTP_200_OK
    for item in resp.data:
        if item['assetId'] == str(any_crypto.uuid):
            assert Decimal(item['totalPrice']) == Decimal('220.0000000')
            break
    else:
        pytest.fail("No required asset record found")
