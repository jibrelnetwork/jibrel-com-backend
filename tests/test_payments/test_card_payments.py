from decimal import Decimal
from functools import partial
from threading import Thread
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from jibrel.accounting.factories import AssetFactory
from jibrel.accounting.models import Asset, Operation
from jibrel.authentication.factories import VerifiedUser
from jibrel.payments.helpers import pretty_operation
from jibrel.payments.models import Fee
from jibrel.payments.tap import (
    create_charge_operation,
    fill_tap_charge_operation
)
from jibrel.payments.tap.base import (
    Card,
    CardListResponse,
    Charge,
    ChargeListResponse,
    ChargeSource,
    ChargeStatus,
    TapCustomer,
    Token,
    Transaction
)
from jibrel.payments.tasks import fetch_charges, process_charge

from .utils import validate_response_schema

captured_charge = Charge(
    id='chg_1234456',
    status=ChargeStatus.CAPTURED,
    amount='1',
    currency='AED',
    threeDSecure=True,
    save_card=True,
    customer=TapCustomer(id="cust_capturedcharge"),
    transaction=Transaction(url="expected_redirect_url"),
    source=ChargeSource(id="tok_123456"),
)


create_customer_mock = mock.patch(
    'jibrel.payments.tap.base.TapClient.create_customer',
    return_value=TapCustomer(id="example1234")
)
get_card_list_mock = mock.patch(
    'jibrel.payments.tap.base.TapClient.get_card_list',
    return_value=CardListResponse([
        Card(customer="cust_1234", id="card_123")
    ])
)
get_card_mock = mock.patch(
    'jibrel.payments.tap.base.TapClient.get_card',
    return_value=Card(customer="cust_1234", id="card_123")
)
create_captured_charge_mock = mock.patch(
    'jibrel.payments.tap.base.TapClient.create_charge',
    return_value=captured_charge
)
get_charge_mock = mock.patch(
    'jibrel.payments.tap.base.TapClient.get_charge',
    return_value=captured_charge
)


@pytest.mark.django_db
@pytest.mark.integration
def test_card_list_integration():
    user = VerifiedUser.create()
    client = APIClient()
    client.force_authenticate(user)

    user.profile.tap_customer_id = None
    user.profile.save()

    resp = client.get('/v1/payments/cards/')
    assert resp.status_code == status.HTTP_200_OK

    user.refresh_from_db()
    assert user.profile.tap_customer_id is not None


@pytest.mark.django_db
def test_card_list():
    user = VerifiedUser.create()
    client = APIClient()
    client.force_authenticate(user)

    user.profile.tap_customer_id = None
    user.profile.save()

    with create_customer_mock, get_card_list_mock:
        resp = client.get('/v1/payments/cards/')

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['data']['customerId'] == "example1234"
    assert resp.data['data']['cards'][0]['id'] == "card_123"

    validate_response_schema('/v1/payments/cards', 'GET', resp)


@pytest.mark.django_db
def test_success_card_deposit():
    user = VerifiedUser.create()
    client = APIClient()
    client.force_authenticate(user)

    with create_customer_mock, get_card_list_mock, create_captured_charge_mock, get_card_mock:
        user.profile.tap_customer_id = 'cust_capturedcharge'
        resp = client.post('/v1/payments/cards/card_123/deposit',
                           data={'amount': '1'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['data']['operationId']

    validate_response_schema('/v1/payments/cards/{cardId}/deposit', 'POST', resp)

    # TODO: check account balance (amount excluding fee)


@pytest.mark.django_db
def test_success_charge():
    user = VerifiedUser.create()
    client = APIClient()
    client.force_authenticate(user)

    user.profile.tap_customer_id = 'cust_capturedcharge'
    user.profile.save()
    with get_charge_mock, get_card_list_mock, get_card_mock:
        resp = client.post('/v1/payments/cards/card_123/charge',
                           data={'charge_id': 'chg_1234456'})

    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_periodic_task():
    user = VerifiedUser.create()
    user.profile.tap_customer_id = 'cust_capturedcharge'
    user.profile.save()

    get_charge_list_mock = mock.patch(
        'jibrel.payments.tap.base.TapClient.get_charge_list',
        return_value=ChargeListResponse([captured_charge])
    )

    get_token_mock = mock.patch(
        'jibrel.payments.tap.base.TapClient.get_token',
        return_value=Token(id='tok_12345', card=Card(id='card_12345', customer='cust_123456'))
    )

    process_task_mock = mock.patch(
        'jibrel.payments.tasks.process_charge.delay'
    )

    with get_charge_list_mock, get_card_mock, get_token_mock, process_task_mock as processing:
        fetch_charges()
        processing.assert_called()

    with get_charge_list_mock, get_card_mock, get_token_mock:
        process_charge(captured_charge)


@pytest.mark.django_db(transaction=True)
def test_fill_operation_race_condition():
    user = VerifiedUser.create()
    asset = AssetFactory.create(type=Asset.FIAT, country=user.get_residency_country_code())
    Fee.objects.get_or_create(
        operation_type=Fee.OPERATION_TYPE_DEPOSIT_CARD,
        asset=asset,
        value_type=Fee.VALUE_TYPE_PERCENTAGE,
        value=Decimal('0.035'),
    )
    operation = Operation.objects.create()
    amount = Decimal('1.00')
    card_id = 'card_1234567'

    reference_operation = create_charge_operation(user, asset, card_id, amount)

    parallel_callable = partial(fill_tap_charge_operation, operation, user, asset, amount, card_id)

    threads = [Thread(target=parallel_callable) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    operation.refresh_from_db()

    assert operation.is_valid(include_new=True)

    assert operation.transactions.count() == reference_operation.transactions.count()

    for ref_tx in reference_operation.transactions.all():
        for tx in operation.transactions.all():
            if ref_tx.account == tx.account and ref_tx.amount == tx.amount:
                break
        else:
            pytest.fail("No reference transaction found %s: Reference: %s Operation: %s" % (
                ref_tx,
                pretty_operation(reference_operation),
                pretty_operation(operation),
            ))
