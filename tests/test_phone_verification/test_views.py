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


@pytest.mark.django_db
def test_change_phone_odd(client, user_with_phone):
    first_phone, second_phone = '+79502216578', '+79502281388'
    url = '/v1/kyc/phone'
    client.force_authenticate(user_with_phone)
    phone = user_with_phone.profile.phone
    phone.number = first_phone
    phone.save()
    response = client.put(url, {'number': first_phone})
    assert response.status_code == 400
    assert user_with_phone.profile.phones.count() == 1
    response = client.put(url, {'number': second_phone})
    assert response.status_code == 200
    response = client.put(url, {'number': second_phone})
    assert response.status_code == 400
    response = client.put(url, {'number': first_phone})
    assert response.status_code == 200
    assert user_with_phone.profile.phones.count() == 2


@pytest.mark.django_db
def test_change_phone_get(client, user_confirmed_email):
    phone_number = '+79502216599'
    url = '/v1/kyc/phone'
    client.force_authenticate(user_confirmed_email)
    response = client.post(url, {'number': phone_number})
    validate_response_schema(url, 'POST', response)
    assert response.status_code == 201
    data_201 = response.data

    response = client.get(url)
    validate_response_schema(url, 'GET', response)
    assert response.status_code == 200
    assert response.data == data_201
    assert response.data['data']['number'] == phone_number[-4:]
