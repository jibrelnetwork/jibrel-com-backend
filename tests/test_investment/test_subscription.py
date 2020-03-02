from uuid import uuid4

import pytest

from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.models import InvestmentSubscription
from tests.factories import VerifiedUser
from tests.test_payments.utils import validate_response_schema

amount = InvestmentSubscription._meta.get_field('amount').choices[1][0]


def apply_subscription(client, offering, data=None):
    data = data or {
        'amount': amount,
        'email': 'absdfba@example.com'
    }
    return client.post(f'/v1/investment/offerings/{offering.pk}/subscribe', data)


@pytest.mark.django_db
def test_subscription_draft_offering(client, full_verified_user, offering, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_user)
    response = apply_subscription(client, offering)
    assert response.status_code == 404
    email_mock.assert_not_called()


@pytest.mark.parametrize(
    'request_data,expected_status',
    (
        (None, 201),
        ({
            'amount': amount,
            'email': 'absdfba@example.com',
        }, 201),
        ({
            'amount': amount,
            'email': 'absdfba@example.com'
        }, 201),
        ({
            'email': 'asdasd'
        }, 400),
        ({
            'email': 'absdfba@example.com',
         }, 400),
        ({
            'email': 'absdfba@example.com'
         }, 400),
        ({
             'amount': amount
         }, 400),
        ({
             'amount': '123',
             'email': 'absdfba@example.com'
         }, 400),
    )
)
@pytest.mark.django_db
def test_subscription(client, full_verified_user, offering_waitlist, request_data, expected_status, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_user)
    response = apply_subscription(client, offering_waitlist, request_data)
    assert response.status_code == expected_status
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)
    email_mock.assert_called() if expected_status == 201 else email_mock.assert_not_called()



@pytest.mark.django_db
def test_subscription_not_authenticated(client, offering_waitlist, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    data = {
        'amount': amount,
        'email': 'absdfba@example.com'
    }
    response = apply_subscription(client, offering_waitlist, data)
    assert response.status_code == 403
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)
    email_mock.assert_not_called()


@pytest.mark.django_db
def test_subscription_organizational(client, full_verified_organisational_user, offering_waitlist, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_organisational_user)

    data = {
        'amount': amount,
        'email': 'absdfba@example.com'
    }
    response = apply_subscription(client, offering_waitlist, data)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)
    sub = InvestmentSubscription.objects.get()
    assert sub.amount == data['amount']
    assert sub.email == data['email']
    assert sub.full_name == str(full_verified_organisational_user.profile.last_kyc.details)
    email_mock.assert_called()


@pytest.mark.django_db
def test_subscription_multiple_users(client, offering_waitlist, mocker):
    mocker.patch('jibrel.investment.signals.handler.email_message_send')
    count = 5
    for i in range(count):
        client.force_login(VerifiedUser.create())
        response = apply_subscription(client, offering_waitlist)
        assert response.status_code == 201
    assert len(set(InvestmentSubscription.objects.values_list('user', flat=True))) == count


@pytest.mark.django_db
def test_subscription_multiple_offerings(client, full_verified_user, offering_factory, mocker):
    mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_user)
    count = 5
    for i in range(count):
        offering = offering_factory(status=OfferingStatus.WAITLIST)
        response = apply_subscription(client, offering)
        assert response.status_code == 201
    assert len(set(InvestmentSubscription.objects.values_list('offering', flat=True))) == count


@pytest.mark.django_db
def test_subscription_exists(client, full_verified_user, offering_waitlist, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_user)
    apply_subscription(client, offering_waitlist)
    response = apply_subscription(client, offering_waitlist)
    assert response.status_code == 409
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)
    email_mock.assert_called_once()


@pytest.mark.django_db
def test_subscription_does_not_exists(client, full_verified_user, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    client.force_login(full_verified_user)
    response = client.post(f'/v1/investment/offerings/{uuid4()}/subscribe', {
        'amount': amount,
        'email': 'absdfba@example.com'
    })
    assert response.status_code == 404
    email_mock.assert_not_called()


@pytest.mark.django_db
def test_subscription_get(client, full_verified_user, offering_waitlist, mocker):
    email_mock = mocker.patch('jibrel.investment.signals.handler.email_message_send')
    url = f'/v1/investment/offerings/{offering_waitlist.uuid}/subscribe'
    client.force_login(full_verified_user)
    response = client.get(url)
    assert response.status_code == 409

    InvestmentSubscription.objects.create(
        offering=offering_waitlist,
        user=full_verified_user,
        amount=amount,
        email='fa67ca9dfded@example.com'
    )
    response = client.get(url)
    assert response.status_code == 200
    email_mock.assert_not_called()
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'GET', response)


@pytest.mark.django_db
def test_subscription_list(client, full_verified_user, offering_factory, mocker):
    url = '/v1/investment/offerings/subscriptions'
    client.force_login(full_verified_user)
    count = 200
    for i in range(count):
        offering = offering_factory(status=OfferingStatus.WAITLIST)
        InvestmentSubscription.objects.create(
            offering=offering,
            user=full_verified_user,
            amount=amount,
            email='fa67ca9dfded@example.com'
        )
    assert len(set(InvestmentSubscription.objects.values_list('offering', flat=True))) == count
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data['data']) == count
