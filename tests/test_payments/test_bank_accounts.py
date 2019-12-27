import os
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django_banking.contrib.wire_transfer.models import UserBankAccount
from django_banking.models import (
    Asset,
    Operation,
    UserAccount
)
from jibrel.authentication.factories import VerifiedUser

from ..test_banking.factories.wire_transfer import (
    BankAccountFactory,
    DepositBankAccountFactory
)
from .utils import validate_response_schema


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.mark.django_db
def test_bank_account_list(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    BankAccountFactory.create(user=user)
    resp = client.get('/v1/payments/bank-account/')
    assert resp.status_code == status.HTTP_200_OK
    validate_response_schema('/v1/payments/bank-account', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'pop_field',
    ['swiftCode', 'bankName', 'holderName', 'ibanNumber']
)
def test_create_account_without_required_fields(client, pop_field):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    body = {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SA0380000000608010167519',
    }
    body.pop(pop_field)
    resp = client.post('/v1/payments/bank-account/', body)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_account_with_invalid_swift(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'WRONG',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_account_with_invalid_iban(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'X',  # invalid
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_account_with_invalid_iban_checksum(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SAW0390000000608010167519',  # invalid
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_account(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/bank-account', 'POST', resp)


@pytest.mark.django_db
def test_create_with_wrong_iban_country(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'Bank name',
        'holderName': 'Abu Dabi',
        'ibanNumber': 'RU0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_with_any_iban_from_oman(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBOMAATRY',
        'bankName': 'Bank name',
        'holderName': 'Abu Dabi',
        'ibanNumber': 'RU0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_invalid_swift_number(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBSAAATRY1',
        'bankName': 'Bank name',
        'holderName': 'Abu Dabi',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_with_wrong_swift_country(settings, client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    # TODO check with real UNSUPPORTED_COUNTRIES
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBXXAATRY',
        'bankName': 'Bank name',
        'holderName': 'Abu Dabi',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_delete_account(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_201_CREATED

    bank_account_id = resp.data["id"]

    resp = client.delete(f'/v1/payments/bank-account/{bank_account_id}/')
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    assert UserBankAccount.objects.filter(pk=bank_account_id, is_active=False).exists()


@pytest.mark.django_db
def test_deposit_request(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBAEAATRY',
        'bankName': 'ZZZ',
        'holderName': 'Y',
        'ibanNumber': 'SA0380000000608010167519',
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/bank-account', 'POST', resp)


@pytest.mark.django_db
def test_success_deposit_request(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    asset = Asset.objects.main_fiat_for_customer(user)
    bank_account = BankAccountFactory.create(user=user, account__asset=asset)

    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)
    uuid = bank_account.uuid
    resp = client.post(f'/v1/payments/bank-account/{uuid}/deposit', {
        'amount': 500
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/bank-account/{bankAccountId}/deposit', 'POST', resp)

    resp = client.get('/v1/payments/operations')

    assert resp.data['data'][0]['userIban'] == bank_account.iban_number[-4:]


@pytest.mark.django_db
def test_negative_deposit_amount(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    uuid = BankAccountFactory.create(user=user).uuid
    resp = client.post(f'/v1/payments/bank-account/{uuid}/deposit', {
        'amount': -10
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_big_deposit_amount(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    uuid = BankAccountFactory.create(user=user).uuid
    resp = client.post(f'/v1/payments/bank-account/{uuid}/deposit', {
        'amount': 7.366139278546699e+30

    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_invalid_deposit_amount(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    uuid = BankAccountFactory.create(user=user).uuid
    resp = client.post(f'/v1/payments/bank-account/{uuid}/deposit', {
        'amount': 'abc',
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_none_bank_account(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.post(f'/v1/payments/bank-account/None/deposit', {
        'amount': '10.0',
    })
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_too_high_precision(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: UserBankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )
    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    op.hold()
    op.commit()
    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': 1.0000000000000012
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_operation_confirmation_upload(settings, client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    bank_account: UserBankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )

    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    UserAccount.objects.get_user_accounts(user)
    assert Operation.objects.filter(transactions__account__in=UserAccount.objects.get_user_accounts(user)).exists()

    with mock.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test') as storage:
        with open(os.path.join(settings.BASE_DIR, 'tests/test_payments/fixtures/upload.jpg'), 'rb') as fp:
            resp = client.post(
                f'/v1/payments/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
    assert resp.status_code == status.HTTP_201_CREATED
    storage.assert_called_once()


@pytest.mark.django_db
def test_unauthorized_upload(settings, client):
    orig_user = VerifiedUser.create()
    client.force_authenticate(orig_user)

    user = VerifiedUser.create()

    bank_account: UserBankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )

    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    with mock.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test') as storage:
        with open(os.path.join(settings.BASE_DIR, 'tests/test_payments/fixtures/upload.jpg'), 'rb') as fp:
            resp = client.post(
                f'/v1/payments/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
        storage.assert_not_called()
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_unauthenticated_upload(settings, client):
    user = VerifiedUser.create()

    bank_account: UserBankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )

    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    UserAccount.objects.get_user_accounts(user)
    assert Operation.objects.filter(
        transactions__account__in=UserAccount.objects.get_user_accounts(
            user)).exists()

    with mock.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test') as storage:
        with open(os.path.join(settings.BASE_DIR, 'tests/test_payments/fixtures/upload.jpg'), 'rb') as fp:
            resp = client.post(
                f'/v1/payments/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        storage.assert_not_called()


@pytest.mark.django_db
def test_deposit_limit_minimum(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    asset = Asset.objects.main_fiat_for_customer(user)

    bank_account: UserBankAccount = BankAccountFactory.create(user=user,
                                                          account__asset=asset)
    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '0.1',
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '30000',
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
