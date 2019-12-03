from decimal import Decimal
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from jibrel.accounting.models import Asset, Operation
from jibrel.authentication.factories import VerifiedUser
from jibrel.payments.factories import (
    BankAccountFactory,
    DepositBankAccountFactory
)
from jibrel.payments.models import (
    BankAccount,
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
def test_create_with_wrong_swift_country(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.post('/v1/payments/bank-account/', {
        'swiftCode': 'ADCBRUAATRY',
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

    assert BankAccount.objects.filter(pk=bank_account_id, is_active=False).exists()


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
    asset = Asset.objects.get(country='AE')
    bank_account = BankAccountFactory.create(user=user, account__asset=asset)

    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)
    uuid = bank_account.uuid
    resp = client.post(f'/v1/payments/bank-account/{uuid}/deposit', {
        'amount': 500
    })
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema('/v1/payments/bank-account/{bankAccountId}/deposit', 'POST', resp)

    resp = client.get('/v1/operations')

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
def test_success_withdrawal(client, set_default_fee_for_operation):
    set_default_fee_for_operation(Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, 0)
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema(
        '/v1/payments/bank-account/{bankAccountId}/withdrawal',
        'POST',
        resp
    )

    resp = client.get('/v1/operations')
    assert resp.data['data'][0]['userIban'] == bank_account.iban_number[-4:]


@pytest.mark.django_db
def test_success_withdrawal_with_fee(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
    Fee.objects.create(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT,
        asset=bank_account.account.asset,
        value=Decimal(35),
        value_type=Fee.VALUE_TYPE_CONSTANT
    )
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )
    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=45
    )
    op.hold()
    op.commit()
    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 45
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED
    validate_response_schema(
        '/v1/payments/bank-account/{bankAccountId}/withdrawal',
        'POST',
        resp
    )


@pytest.mark.django_db
def test_too_high_precision(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 1.0000000000000012
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_insufficient_funds_withdrawal(client, set_default_fee_for_operation):
    set_default_fee_for_operation(Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, 0)
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 100
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_insufficient_funds_withdrawal_with_fee(client, set_default_fee_for_operation):
    set_default_fee_for_operation(Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, 0)
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
    Fee.objects.create(
        operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT,
        asset=bank_account.account.asset,
        value=Decimal(35),
        value_type=Fee.VALUE_TYPE_CONSTANT
    )
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
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_hold_conflict_withdrawal(client, set_default_fee_for_operation):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    bank_account: BankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )
    fee_account = FeeUserAccount.objects.for_customer(
        user, bank_account.account.asset
    )
    fee_amount = 0
    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    op.hold()
    op.commit()
    op = Operation.objects.create_withdrawal(
        user_account=user_account,
        payment_method_account=bank_account.account,
        amount=10,
        fee_account=fee_account,
        fee_amount=fee_amount,
        rounding_account=RoundingUserAccount.objects.for_customer(user, user_account.asset),
        rounding_amount=0
    )
    op.hold()
    set_default_fee_for_operation(Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, 0)
    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': 10
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_operation_confirmation_upload(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
        with open('tests/test_payments/fixtures/upload.jpg', 'rb') as fp:
            resp = client.post(
                f'/v1/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
    assert resp.status_code == status.HTTP_201_CREATED
    storage.assert_called_once()


@pytest.mark.django_db
def test_unauthorized_upload(client):
    orig_user = VerifiedUser.create()
    client.force_authenticate(orig_user)

    user = VerifiedUser.create()

    bank_account: BankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )

    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    with mock.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test') as storage:
        with open('tests/test_payments/fixtures/upload.jpg', 'rb') as fp:
            resp = client.post(
                f'/v1/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
        storage.assert_not_called()
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_unauthenticated_upload(client):
    user = VerifiedUser.create()

    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
        with open('tests/test_payments/fixtures/upload.jpg', 'rb') as fp:
            resp = client.post(
                f'/v1/operations/{op.uuid}/upload',
                {
                    'file': fp
                },
                format='multipart'
            )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        storage.assert_not_called()


@pytest.mark.usefixtures('off_fees')
@pytest.mark.django_db
def test_withdrawal_limit_exceed(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    asset = Asset.objects.get(country=user.get_residency_country_code())

    bank_account: BankAccount = BankAccountFactory.create(user=user,
                                                          account__asset=asset)
    user_account = UserAccount.objects.for_customer(user, asset)

    # deposit funds amount greater than limits
    Operation.objects.create_deposit(
        bank_account.account,
        user_account=user_account,
        amount=100000
    ).commit()

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': '90000.0',
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': '30000.0',
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': '30000.0',
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_deposit_limit_exceed(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)

    asset = Asset.objects.get(country=user.get_residency_country_code())

    bank_account: BankAccount = BankAccountFactory.create(user=user,
                                                          account__asset=asset)
    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '60000',
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

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '30000',
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '10000',
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_deposit_advanced(client):
    user = VerifiedUser.create(profile__kyc_status='advanced')
    client.force_authenticate(user)

    asset = Asset.objects.get(country=user.get_residency_country_code())
    bank_account: BankAccount = BankAccountFactory.create(user=user,
                                                          account__asset=asset)
    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': '30000',
        }
    )
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    'country,expected_fee,amount',
    (
        ('AE', Decimal(0), Decimal(1)),
        ('SA', Decimal(0), Decimal(1)),
        ('BH', Decimal(0), Decimal(1)),
        ('KW', Decimal(0), Decimal(1)),
        ('OM', Decimal(0), Decimal(1)),

        ('AE', Decimal(35), Decimal(1)),
        ('SA', Decimal(35), Decimal(1)),
        ('BH', Decimal(3), Decimal(1)),
        ('KW', Decimal(3), Decimal(1)),
        ('OM', Decimal(3), Decimal(1)),

        ('AE', Decimal(35), Decimal('2.25')),
        ('SA', Decimal(35), Decimal('2.25')),
        ('BH', Decimal(3), Decimal('2.25')),
        ('KW', Decimal(3), Decimal('2.25')),
        ('OM', Decimal(3), Decimal('2.25')),

        ('AE', Decimal(35), Decimal(100)),
        ('SA', Decimal(35), Decimal(100)),
        ('BH', Decimal(3), Decimal(100)),
        ('KW', Decimal(3), Decimal(100)),
        ('OM', Decimal(3), Decimal(100)),

        ('AE', Decimal(35), Decimal(1000)),
        ('SA', Decimal(35), Decimal(1000)),
        ('BH', Decimal(3), Decimal(1000)),
        ('KW', Decimal(3), Decimal(1000)),
        ('OM', Decimal(3), Decimal(1000)),
    )
)
@pytest.mark.django_db
def test_bank_account_calculate_withdrawal(country, expected_fee, amount, client, full_verified_user_factory):
    user = full_verified_user_factory(country)
    client.force_authenticate(user)
    asset = Asset.objects.get(country=user.get_residency_country_code())
    bank_account: BankAccount = BankAccountFactory.create(user=user, account__asset=asset)

    Fee.objects.filter(operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT, asset=asset).update(
        value_type=Fee.VALUE_TYPE_CONSTANT, value=expected_fee
    )

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal/calculate',
        {
            'amount': str(amount),
        }
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    assert Decimal(resp.data['data']['fee']) == expected_fee
    assert Decimal(resp.data['data']['amount']) == amount
    assert Decimal(resp.data['data']['total']) == amount - expected_fee


@pytest.mark.parametrize(
    'country,limit,amount,expected_status',
    (
        # # positive
        ('AE', Decimal(500), Decimal(500), 201),
        ('SA', Decimal(500), Decimal(500), 201),
        ('BH', Decimal(50), Decimal(50), 201),
        ('KW', Decimal(40), Decimal(40), 201),
        ('OM', Decimal(50), Decimal(50), 201),
        # negative
        ('AE', Decimal(500), Decimal(500 - 1), 400),
        ('SA', Decimal(500), Decimal(500 - 1), 400),
        ('BH', Decimal(50), Decimal(50 - 1), 400),
        ('KW', Decimal(40), Decimal(40 - 1), 400),
        ('OM', Decimal(50), Decimal(50 - 1), 400),
    )
)
@pytest.mark.django_db
def test_operation_min_limit(country, limit, amount, expected_status, client, full_verified_user_factory):
    user = full_verified_user_factory(country)
    client.force_authenticate(user)
    asset = Asset.objects.get(country=user.get_residency_country_code())

    bank_account: BankAccount = BankAccountFactory.create(user=user, account__asset=asset)
    DepositBankAccountFactory.create(account__asset=bank_account.account.asset)
    user_account = UserAccount.objects.for_customer(user, asset)

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/deposit',
        {
            'amount': amount,
        }
    )

    assert resp.status_code == expected_status, resp.content

    Operation.objects.create_deposit(
        bank_account.account,
        user_account=user_account,
        amount=amount
    ).commit()

    resp = client.post(
        f'/v1/payments/bank-account/{bank_account.uuid}/withdrawal',
        {
            'amount': str(amount),
        }
    )
    assert resp.status_code == expected_status, resp.content
