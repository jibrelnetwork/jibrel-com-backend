from datetime import (
    date,
    timedelta
)

import pytest

from jibrel.authentication.factories import KYCDocumentFactory
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
            'amlAgreed': True,
            'uboConfirmed': True,
            'step': 0
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
        ([], {'step': 1}, 200),
        ([], {'step': 2}, 200),
        ([], {'step': 3}, 200),
        (['firstName'], {}, 400),
        (['middleName'], {}, 200),
        (['apartment'], {'step': 1}, 200),
        (['postCode'], {'step': 1}, 200),
        (['country'], {'step': 1}, 400),
        (['occupation'], {'step': 2, 'occupationOther': 'other'}, 200),
        (['incomeSource'], {'step': 2, 'incomeSourceOther': 'other'}, 200),
        (['occupation'], {'step': 2}, 400),
        ([], {'step': 2, 'occupation': ''}, 400),
        (['incomeSource'], {'step': 2}, 400),
        ([], {'step': 2, 'incomeSource': ''}, 400),
        ([], {'birthDate': format_date(date.today() - timedelta(days=366 * 18))}, 400),
        ([], {'step': 3, 'passportExpirationDate': format_date(date.today())}, 400),
        ([], {'amlAgreed': False}, 200),
        ([], {'uboConfirmed': False}, 200),
    )
)
@pytest.mark.django_db
def test_individual_kyc_validate(
    client,
    user_with_confirmed_phone,
    get_payload,
    remove_fields,
    overrides,
    expected_status_code,
):
    url = '/v1/kyc/individual/validate'
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        url,
        get_payload(user_with_confirmed_phone.profile, *remove_fields, **overrides)
    )

    assert response.status_code == expected_status_code, response.content
    validate_response_schema(url, 'POST', response)
