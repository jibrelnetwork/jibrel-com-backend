from decimal import Decimal

import pytest
from django.db.models import Sum
from rest_framework import status
from rest_framework.test import APIClient

from jibrel.accounting.factories import AssetFactory
from jibrel.accounting.models import (
    Asset,
    Operation,
    Transaction
)
from jibrel.authentication.factories import VerifiedUser
from jibrel.payments.factories import (
    CryptoAccountFactory,
    DepositCryptoAccountFactory
)
from jibrel.payments.models import (
    CryptoAccount,
    Fee,
    FeeUserAccount,
    RoundingUserAccount,
    UserAccount
)

from .utils import validate_response_schema


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.mark.django_db
def test_cryptoaccount_list(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    CryptoAccountFactory.create(user=user)
    resp = client.get('/v1/payments/cryptocurrency/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    validate_response_schema('/v1/payments/cryptocurrency', 'GET', resp)


@pytest.mark.django_db
def test_create_cryptoaccount(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    asset = AssetFactory()
    resp = client.post('/v1/payments/cryptocurrency/', {
        'assetId': asset.uuid,
        'address': '0x1112222333'
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/cryptocurrency', 'POST', resp)

    resp = client.get('/v1/payments/cryptocurrency/')
    assert len(resp.data) == 1


@pytest.mark.django_db
def test_delete_cryptoaccount(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    asset = AssetFactory()
    resp = client.post('/v1/payments/cryptocurrency/', {
        'assetId': asset.uuid,
        'address': '0x1112222333'
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/cryptocurrency', 'POST', resp)

    crypto_account_id = resp.data["id"]

    resp = client.delete(f'/v1/payments/cryptocurrency/{crypto_account_id}/')
    assert resp.status_code == 204

    assert CryptoAccount.objects.filter(pk=crypto_account_id, is_active=False).exists()


@pytest.mark.django_db
def test_create_cryptoaccount_wrong_asset(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.post('/v1/payments/cryptocurrency/', {
        'address': '0x111'
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = client.post('/v1/payments/cryptocurrency/', {
        'assetId': '123',
        'address': '0x111'
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_deposit_endpoint(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    asset = AssetFactory.create()
    deposit_account = DepositCryptoAccountFactory.create(account__asset=asset)
    resp = client.get(f'/v1/payments/cryptocurrency/deposit/{asset.uuid}/')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['address'] == deposit_account.address
    assert 'address' in resp.data
    validate_response_schema(
        '/v1/payments/cryptocurrency/deposit/{assetId}',
        'GET',
        resp
    )

    Operation.objects.create_deposit(
        payment_method_account=deposit_account.account,
        user_account=UserAccount.objects.for_customer(user, asset),
        amount=10
    ).commit()

    resp = client.get('/v1/operations')
    assert resp.status_code == status.HTTP_200_OK

    assert resp.data['data'][0]['cryptoDepositAddress'] == deposit_account.address


@pytest.mark.usefixtures('off_fees')
@pytest.mark.django_db
def test_success_withdrawal(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    crypto_account = CryptoAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, crypto_account.account.asset
    )

    # deposit some funds
    op = Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=10
    )
    op.commit()

    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/cryptocurrency/{cryptocurrencyAccountId}/withdrawal', 'POST', resp)


@pytest.mark.django_db
def test_success_withdrawal_with_fee(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    crypto_account = CryptoAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, crypto_account.account.asset
    )
    Fee.objects.create(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT,
        asset=crypto_account.account.asset,
        value=Decimal('0.015'),
        value_type=Fee.VALUE_TYPE_PERCENTAGE
    )
    # deposit some funds
    op = Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=Decimal('11.5')
    )
    op.commit()

    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/cryptocurrency/{cryptocurrencyAccountId}/withdrawal', 'POST', resp)

@pytest.mark.usefixtures('off_fees')
@pytest.mark.django_db
def test_withdrawal_confirmation(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    crypto_account = CryptoAccountFactory.create(user=user)
    assert not FeeUserAccount.objects.filter(account=crypto_account.account).exists()
    user_account = UserAccount.objects.for_customer(
        user, crypto_account.account.asset
    )

    # deposit some funds
    op = Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=10
    )
    op.commit()

    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema(
        '/v1/payments/cryptocurrency/{cryptocurrencyAccountId}/withdrawal',
        'POST',
        resp
    )

    operation_id = resp.data['id']
    op = Operation.objects.get(pk=operation_id)
    token = op.references['confirmation_token']
    resp = client.get(f'/v1/operations/{operation_id}/confirm?key={token}')
    assert resp.status_code == status.HTTP_200_OK

    op = Operation.objects.get(pk=operation_id)
    assert op.status == Operation.HOLD


@pytest.mark.usefixtures('off_fees')
@pytest.mark.django_db
def test_overspent(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    crypto_account = CryptoAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, crypto_account.account.asset
    )
    op = Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=10
    )
    op.commit()
    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': 20
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_overspent_with_fee(client: APIClient):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    crypto_account = CryptoAccountFactory.create(user=user)
    Fee.objects.create(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT,
        asset=crypto_account.account.asset,
        value=Decimal('0.015'),
        value_type=Fee.VALUE_TYPE_PERCENTAGE
    )
    user_account = UserAccount.objects.for_customer(
        user, crypto_account.account.asset
    )
    op = Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=10
    )
    op.commit()
    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': 20
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    'currency,precision,fee_value,amount,expected_fee',
    (
        ('BTC', 8, Decimal(0), Decimal(1), Decimal(0)),
        ('ETH', 8, Decimal(0), Decimal(1), Decimal(0)),
        ('XRP', 8, Decimal(0), Decimal(1), Decimal(0)),
        ('LTC', 8, Decimal(0), Decimal(1), Decimal(0)),
        ('BCH', 8, Decimal(0), Decimal(1), Decimal(0)),

        ('BTC', 8, Decimal('0.015'), Decimal(1), Decimal('0.015')),
        ('ETH', 8, Decimal('0.015'), Decimal(1), Decimal('0.015')),
        ('XRP', 8, Decimal('0.015'), Decimal(1), Decimal('0.015')),
        ('LTC', 8, Decimal('0.015'), Decimal(1), Decimal('0.015')),
        ('BCH', 8, Decimal('0.015'), Decimal(1), Decimal('0.015')),

        ('BTC', 8, Decimal('0.015'), Decimal('0.00000001'), Decimal('0.00000000')),
        ('ETH', 8, Decimal('0.015'), Decimal('0.00000001'), Decimal('0.00000000')),
        ('XRP', 8, Decimal('0.015'), Decimal('0.00000001'), Decimal('0.00000000')),
        ('LTC', 8, Decimal('0.015'), Decimal('0.00000001'), Decimal('0.00000000')),
        ('BCH', 8, Decimal('0.015'), Decimal('0.00000001'), Decimal('0.00000000')),

        ('BTC', 8, Decimal('0.015'), Decimal('0.00001'), Decimal('0.00000015')),
        ('ETH', 8, Decimal('0.015'), Decimal('0.00001'), Decimal('0.00000015')),
        ('XRP', 8, Decimal('0.015'), Decimal('0.00001'), Decimal('0.00000015')),
        ('LTC', 8, Decimal('0.015'), Decimal('0.00001'), Decimal('0.00000015')),
        ('BCH', 8, Decimal('0.015'), Decimal('0.00001'), Decimal('0.00000015')),

        ('BTC', 8, Decimal(1), Decimal(1), Decimal(1)),
        ('ETH', 8, Decimal(1), Decimal(1), Decimal(1)),
        ('XRP', 8, Decimal(1), Decimal(1), Decimal(1)),
        ('LTC', 8, Decimal(1), Decimal(1), Decimal(1)),
        ('BCH', 8, Decimal(1), Decimal(1), Decimal(1)),
    )
)
@pytest.mark.django_db
def test_crypto_account_calculate_withdrawal(
    currency,
    precision,
    fee_value,
    amount,
    expected_fee,
    client,
    full_verified_user
):
    client.force_authenticate(full_verified_user)
    asset = Asset.objects.get(symbol=currency)
    asset.decimals = precision
    asset.save()

    Fee.objects.filter(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_CRYPTO
    ).update(
        value_type=Fee.VALUE_TYPE_PERCENTAGE, value=fee_value
    )

    resp = client.post(
        f'/v1/payments/cryptocurrency/withdrawal/{asset.uuid}/calculate',
        {
            'amount': str(amount),
        }
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    assert Decimal(resp.data['data']['fee']) == expected_fee
    assert Decimal(resp.data['data']['amount']) == amount
    assert Decimal(resp.data['data']['total']) == amount - expected_fee


@pytest.mark.django_db
def test_positive_withdrawal_crypto_with_rounding(
    client,
    full_verified_user,
    mocker,
):
    client.force_authenticate(full_verified_user)
    asset = Asset.objects.get(symbol='BTC')
    asset.decimals = 6
    asset.save()
    Fee.objects.filter(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_CRYPTO
    ).update(
        value_type=Fee.VALUE_TYPE_PERCENTAGE, value=Decimal('0.015')
    )
    crypto_account = CryptoAccountFactory.create(user=full_verified_user, account__asset=asset)
    user_account = UserAccount.objects.for_customer(
        full_verified_user, crypto_account.account.asset
    )
    Operation.objects.create_deposit(
        payment_method_account=crypto_account.account,
        user_account=user_account,
        amount=10
    ).commit()
    mocker.patch('jibrel.payments.views.CryptoAccountWithdrawalAPIView.get_metadata', return_value={})
    resp = client.post(
        f'/v1/payments/cryptocurrency/{crypto_account.uuid}/withdrawal/',
        {
            'amount': '1.234567',
        }
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    assert Decimal(resp.data['feeAmount']) == Decimal('0.018518'), resp.content
    assert Decimal(resp.data['creditAmount']) == Decimal('1.234567'), resp.content

    op_id = resp.data['id']
    remainder = Transaction.objects.filter(
        account__in=RoundingUserAccount.objects.values_list('account', flat=True),
        operation=op_id
    ).aggregate(remainder=Sum('amount')).get('remainder')
    assert remainder == Decimal('-0.000001'), remainder
