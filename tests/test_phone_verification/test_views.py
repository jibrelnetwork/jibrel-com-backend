import pytest
from rest_framework.test import APIClient

from tests.test_payments.utils import validate_response_schema


@pytest.fixture()
def client():
    return APIClient()


@pytest.mark.parametrize(
    'phone_number,expected_status',
    (
        ('+79502216578', 201),
        ('+123', 400),
        ('qsw', 400),
    )
)
@pytest.mark.django_db
def test_submit_phone(client, user_confirmed_email, phone_number, expected_status):
    url = '/v1/kyc/phone'
    client.force_authenticate(user_confirmed_email)

    response = client.post(url, {'number': phone_number})
    validate_response_schema(url, 'POST', response)
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    'previous_phone,phone_number,expected_status',
    (
        ('+79502216578', '+79502281388', 200),
        ('+79502216578', '+79502216578', 400),
        ('+79502216578', '+123', 400),
        ('+79502216578', 'qsw', 400),
    )
)
@pytest.mark.django_db
def test_change_phone(client, user_with_phone, previous_phone, phone_number, expected_status):
    url = '/v1/kyc/phone'
    client.force_authenticate(user_with_phone)
    phone = user_with_phone.profile.phone
    phone.number = previous_phone
    phone.save()
    response = client.put(url, {'number': phone_number})
    validate_response_schema(url, 'PUT', response)
    assert response.status_code == expected_status
