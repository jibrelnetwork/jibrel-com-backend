from datetime import (
    date,
    timedelta
)

import pytest

from jibrel.authentication.factories import KYCDocumentFactory
from jibrel.authentication.models import Profile
from tests.test_payments.utils import validate_response_schema


def format_date(d: date):
    return d.strftime('%Y-%m-%d')


@pytest.fixture
def get_payload(db):
    def _get_payload(profile, *remove_fields, **overrides):
        data = {
            'firstName': 'First name',
            'middleName': 'Middle name',
            'lastName': 'Last name',
            'birthDate': format_date(date.today() - timedelta(days=366 * 22)),
            'nationality': 'ae',
            'streetAddress': 'Street address',
            'apartment': '82',
            'postCode': '1234',
            'city': 'City',
            'country': 'ae',
            'occupation': 'marketing',
            'incomeSource': 'sale_assets',
            'passportNumber': '1234',
            'passportExpirationDate': format_date(date.today() + timedelta(days=30 * 2)),
            'passportDocument': str(KYCDocumentFactory(profile=profile).pk),
            'proofOfAddressDocument': str(KYCDocumentFactory(profile=profile).pk),
        }
        for f in remove_fields:
            del data[f]
        return {
            **data,
            **overrides,
        }

    return _get_payload


@pytest.mark.parametrize(
    'remove_fields,overrides,expected_status_code',
    (
        ([], {}, 200),
        ([], {'firstName': "D'ark", 'middleName': "D'ark", 'lastName': "D'ark"}, 200),
        (['middleName'], {}, 200),
        (['apartment'], {}, 200),
        (['postCode'], {}, 200),
        ([], {'occupation': 'other'}, 200),
        ([], {'incomeSource': 'other'}, 200),

        (['occupation'], {}, 400),
        (['incomeSource'], {}, 400),
        ([], {'birthDate': format_date(date.today() - timedelta(days=366 * 18))}, 400),
        ([], {'passportExpirationDate': format_date(date.today())}, 400),
    )
)
@pytest.mark.django_db
def test_individual_kyc(
    client,
    user_with_confirmed_phone,
    get_payload,
    remove_fields,
    overrides,
    expected_status_code,
    mocker,
):
    url = '/v1/kyc/individual'
    onfido_mock = mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    email_mock = mocker.patch('jibrel.kyc.signals.handler.email_message_send')
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        url,
        get_payload(user_with_confirmed_phone.profile, *remove_fields, **overrides)
    )

    assert response.status_code == expected_status_code, response.content
    validate_response_schema(url, 'POST', response)
    if expected_status_code == 200:
        onfido_mock.assert_called()
        email_mock.assert_called()
        assert Profile.objects.get(user=user_with_confirmed_phone).kyc_status == Profile.KYC_PENDING
    else:
        onfido_mock.assert_not_called()
        email_mock.assert_not_called()
