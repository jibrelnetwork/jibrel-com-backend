import os
from unittest import mock

import pytest
from django.conf import settings
from django.core.files import File
from rest_framework import status
from rest_framework.test import APIClient

from django_banking.models import (
    Asset,
    Operation,
    UserAccount
)
from django_banking.models.transactions.enum import OperationType
from django_banking.models.transactions.models import (
    OperationConfirmationDocument
)
from jibrel.authentication.factories import (
    ApprovedKYCFactory,
    VerifiedUser
)

from ..test_banking.factories.dajngo_banking import AccountFactory
from .utils import validate_response_schema


def create_deposit_operation(user, commit=True):
    operation = Operation.objects.create(type=OperationType.DEPOSIT, references={
        'reference_code': '1234'
    })
    asset = Asset.objects.main_fiat_for_customer(user)
    user_account = UserAccount.objects.for_customer(user, asset)
    second_account = AccountFactory.create(asset=asset)

    operation.transactions.create(account=user_account, amount=10)
    operation.transactions.create(account=second_account, amount=-10)

    operation.hold()
    if commit:
        operation.commit()

    return operation


def create_withdrawal_operation(user, commit=True):
    operation = Operation.objects.create(type=OperationType.WITHDRAWAL, references={
        'reference_code': '1234'
    })
    asset = Asset.objects.main_fiat_for_customer(user)
    user_account = UserAccount.objects.for_customer(user, asset)
    second_account = AccountFactory.create(asset=user_account.asset)

    operation.transactions.create(account=user_account, amount=-10)
    operation.transactions.create(account=second_account, amount=10)

    operation.hold()
    if commit:
        operation.commit()

    return operation


@pytest.mark.django_db
def test_operations_list():
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.get('/v1/payments/operations/')

    assert resp.status_code == 200
    assert len(resp.data['data']) == 0

    create_deposit_operation(user)
    operation = create_deposit_operation(user)

    resp = client.get('/v1/payments/operations/')

    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data['data']) == 2
    assert resp.data['data'][0]['id'] == str(operation.uuid)
    assert resp.data['data'][0]['debitAmount'] == '10.000000'
    validate_response_schema('/v1/payments/operations', 'GET', resp)


@pytest.mark.django_db
def test_bank_deposit_with_upload():
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)

    operation = create_deposit_operation(user, commit=False)

    resp = client.get('/v1/payments/operations/')
    assert resp.data['data'][0]['status'] == 'waiting_payment'

    with mock.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test'):
        with open(os.path.join(settings.BASE_DIR, 'tests/test_payments/fixtures/upload.jpg'), 'rb') as fp:
            doc_file = File(fp)
            OperationConfirmationDocument.objects.create(
                operation=operation,
                file=doc_file
            )

    with mock.patch('django_banking.api.serializers.DepositOperationSerializer.get_confirmation_document',
                    return_value="http://url"):
        resp = client.get('/v1/payments/operations/')

    assert resp.data['data'][0]['status'] == 'processing'
    assert resp.data['data'][0]['confirmationDocument'] == "http://url"
    assert resp.data['data'][0]['depositReferenceCode'] == '1234'


@pytest.mark.django_db
def test_operation_details():
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)

    operation = create_deposit_operation(user)

    resp = client.get(f'/v1/payments/operations/{operation.uuid}')
    assert resp.status_code == status.HTTP_200_OK
    validate_response_schema('/v1/payments/operations/{operationId}', 'GET', resp)


@pytest.mark.django_db
def test_operation_after_citizenship_change():
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)

    operation = create_deposit_operation(user)

    kyc_submission = ApprovedKYCFactory.create(
        profile=user.profile,
        passport_document__profile=user.profile,
        proof_of_address_document__profile=user.profile,
        nationality='om',
        country='om'
    )
    user.profile.last_basic_kyc = kyc_submission
    user.profile.save(update_fields=('last_kyc',))

    resp = client.get('/v1/payments/operations')
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data['data']) == 1
    assert resp.data['data'][0]['id'] == str(operation.uuid)

    resp = client.get(f'/v1/payments/operations/{operation.uuid}')
    assert resp.status_code == status.HTTP_200_OK
