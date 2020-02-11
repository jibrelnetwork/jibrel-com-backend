from uuid import uuid4

import pytest

from jibrel.authentication.factories import VerifiedUser
from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.models import InvestmentSubscription
from tests.test_payments.utils import validate_response_schema


def apply_subscription(client, offering, data=None):
    data = data or {
        'amount': 1,
        'email': 'absdfba@gmail.com'
    }
    return client.post(f'/v1/investment/offerings/{offering.pk}/subscribe', data)


@pytest.mark.django_db
def test_subscription_draft_offering(client, full_verified_user, offering):
    client.force_login(full_verified_user)
    response = apply_subscription(client, offering)
    assert response.status_code == 404


@pytest.mark.parametrize(
    'request_data,expected_status',
    (
        (None, 201),
        ({
            'amount': 1,
            'email': 'absdfba@gmail.com',
        }, 201),
        ({
            'amount': 1,
            'email': 'absdfba@gmail.com'
        }, 201),
        ({
            'email': 'asdasd'
        }, 400),
        ({
            'email': 'absdfba@gmail.com',
         }, 400),
        ({
            'email': 'absdfba@gmail.com'
         }, 400),
        ({
             'amount': '4'
         }, 400),
    )
)
@pytest.mark.django_db
def test_subscription(client, full_verified_user, offering_waitlist, request_data, expected_status):
    client.force_login(full_verified_user)
    response = apply_subscription(client, offering_waitlist, request_data)
    assert response.status_code == expected_status
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)


@pytest.mark.django_db
def test_subscription_not_authenticated(client, offering_waitlist):
    data = {
        'amount': 1,
        'email': 'absdfba@gmail.com'
    }
    response = apply_subscription(client, offering_waitlist, data)
    assert response.status_code == 403
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)


@pytest.mark.django_db
def test_subscription_organizational(client, full_verified_organisational_user, offering_waitlist):
    client.force_login(full_verified_organisational_user)

    data = {
        'amount': 1,
        'email': 'absdfba@gmail.com'
    }
    response = apply_subscription(client, offering_waitlist, data)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)
    sub = InvestmentSubscription.objects.get()
    assert sub.amount == data['amount']
    assert sub.email == data['email']
    assert sub.full_name == str(full_verified_organisational_user.profile.last_kyc.details)


@pytest.mark.django_db
def test_subscription_multiple_users(client, offering_waitlist):
    count = 5
    for i in range(count):
        client.force_login(VerifiedUser.create())
        response = apply_subscription(client, offering_waitlist)
        assert response.status_code == 201
    assert len(set(InvestmentSubscription.objects.values_list('user', flat=True))) == count


@pytest.mark.django_db
def test_subscription_multiple_offerings(client, full_verified_user, offering_factory):
    client.force_login(full_verified_user)
    count = 5
    for i in range(count):
        offering = offering_factory(status=OfferingStatus.WAITLIST)
        response = apply_subscription(client, offering)
        assert response.status_code == 201
    assert len(set(InvestmentSubscription.objects.values_list('offering', flat=True))) == count


@pytest.mark.django_db
def test_subscription_exists(client, full_verified_user, offering_waitlist):
    client.force_login(full_verified_user)
    apply_subscription(client, offering_waitlist)
    response = apply_subscription(client, offering_waitlist)
    assert response.status_code == 409
    validate_response_schema('/v1/investment/offerings/{offeringId}/subscribe', 'POST', response)


@pytest.mark.django_db
def test_subscription_does_not_exists(client, full_verified_user):
    client.force_login(full_verified_user)
    response = client.post(f'/v1/investment/offerings/{uuid4()}/subscribe', {
        'amount': 1,
        'email': 'absdfba@gmail.com'
    })
    print(response.data)
    assert response.status_code == 404
