from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django_banking.models import (
    Asset,
    UserAccount
)
from django_banking.models.assets.enum import AssetType
from tests.factories import VerifiedUser

from ..test_banking.factories.dajngo_banking import AccountFactory
from .utils import validate_response_schema


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
def test_balance_with_transactions(client, full_verified_user, create_deposit_operation):
    client.force_authenticate(full_verified_user)
    usd = Asset.objects.filter(type=AssetType.FIAT).first()
    user_account = UserAccount.objects.for_customer(full_verified_user, usd)
    payment_method_account = AccountFactory.create(asset=usd)

    create_deposit_operation(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('100.00')
    )

    create_deposit_operation(
        payment_method_account=payment_method_account,
        user_account=user_account,
        amount=Decimal('10.00')
    )

    resp = client.get('/v1/payments/balance/')
    validate_response_schema('/v1/payments/balance', 'GET', resp)
    assert resp.data['balance'] == '110.00'
