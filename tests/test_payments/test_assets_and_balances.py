from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django_banking.models import Asset, Operation, UserAccount
from django_banking.models.assets.enum import AssetType
from jibrel.authentication.factories import VerifiedUser

from .utils import validate_response_schema
from ..test_banking.factories.dajngo_banking import AccountFactory


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.mark.django_db
def test_assets_list(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.get('/v1/payments/assets/')
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)
    assert len(resp.data) == Asset.objects.all().count()
    validate_response_schema('/v1/payments/assets', 'GET', resp)


@pytest.mark.django_db
def test_balance(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.get('/v1/payments/balance/')
    validate_response_schema('/v1/payments/balance', 'GET', resp)
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, dict)


@pytest.mark.django_db
def test_balance_with_transactions(client, full_verified_user):
    client.force_authenticate(full_verified_user)
    usd = Asset.objects.filter(type=AssetType.FIAT).first()
    user_account = UserAccount.objects.for_customer(full_verified_user, usd)
    payment_method_account = AccountFactory.create(asset=usd)

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

    resp = client.get('/v1/payments/balance/')
    validate_response_schema('/v1/payments/balance', 'GET', resp)
    assert resp.data['balance'] == '110.00'


# @pytest.mark.django_db
# def test_totalfiat_balance(set_price, client, full_verified_user):
#     client.force_authenticate(full_verified_user)
#     usd = Asset.objects.filter(type=AssetType.FIAT).first()
#     user_account = UserAccount.objects.for_customer(full_verified_user, usd)
#     payment_method_account = AccountFactory.create(asset=usd)
#
#     user_country_code = full_verified_user.get_residency_country_code()
#     user_currency = Asset.objects.get(country=user_country_code)
#
#     pair = AssetPair.objects.get(base=any_crypto, quote=user_currency)
#     set_price(
#         pair, Decimal('2.0'), Decimal('2.0'),
#         intermediate_crypto_buy_price=Decimal('2.0'),
#         intermediate_fiat_buy_price=Decimal('2.0')
#     )
#
#     Operation.objects.create_deposit(
#         payment_method_account=payment_method_account,
#         user_account=user_account,
#         amount=Decimal('100.00')
#     ).commit()
#
#     Operation.objects.create_deposit(
#         payment_method_account=payment_method_account,
#         user_account=user_account,
#         amount=Decimal('10.00')
#     ).commit()
#
#     resp = client.get('/v1/balance/')
#
#     assert resp.status_code == status.HTTP_200_OK
#     for item in resp.data:
#         if item['assetId'] == str(any_crypto.uuid):
#             assert Decimal(item['totalPrice']) == Decimal('220.0000000')
#             break
#     else:
#         pytest.fail("No required asset record found")
