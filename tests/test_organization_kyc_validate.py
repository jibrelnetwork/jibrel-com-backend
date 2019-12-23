from datetime import (
    date,
    timedelta
)

import pytest

from jibrel.authentication.factories import KYCDocumentFactory
from tests.test_payments.utils import validate_response_schema

DATE_FORMAT = '%Y-%m-%d'


def format_date(d: date):
    return d.strftime(DATE_FORMAT)


@pytest.fixture
def get_payload(db):
    def _get_payload(profile, *remove_fields, **overrides):
        registered_address = {
            'streetAddress': 'Reg street 1',
            'apartment': 'Reg apart 1',
            'postCode': '1111',
            'city': 'Reg City 1',
            'country': 'us',
        }

        principal_address = {
            'streetAddress': 'Principal street 1',
            'apartment': 'Principal apart 1',
            'postCode': '1222',
            'city': 'Principal City 1',
            'country': 'ru',
        }

        beneficiaries = [
            {
                'fullName': 'Full name b one',
                'birthDate': '1960-01-01',
                'nationality': 'ae',
                'email': 'b1@email.com',
                'phoneNumber': '+79991112233',
                'streetAddress': 'Street address b1',
                'apartment': '111',
                'postCode': '1111',
                'city': 'City b1',
                'country': 'ae',
                'passportNumber': '1234',
                'passportExpirationDate': format_date(date.today() + timedelta(days=30 * 2)),
                'passportDocument': str(KYCDocumentFactory(profile=profile).pk),
                'proofOfAddressDocument': str(KYCDocumentFactory(profile=profile).pk),
            },
            {
                'fullName': 'Full name b two',
                'birthDate': '1960-01-02',
                'nationality': 'ae',
                'email': 'b2@email.com',
                'phoneNumber': '+79901112233',
                'streetAddress': 'Street address b2',
                'apartment': '222',
                'postCode': '2222',
                'city': 'City b2',
                'country': 'ae',
                'passportNumber': '1234',
                'passportExpirationDate': format_date(date.today() + timedelta(days=30 * 2)),
                'passportDocument': str(KYCDocumentFactory(profile=profile).pk),
                'proofOfAddressDocument': str(KYCDocumentFactory(profile=profile).pk),
            },
        ]

        directors = [
            {
                'fullName': 'Full name d one',
            },
            {
                'fullName': 'Full name d two',
            },
        ]

        data = {
            'firstName': 'First name',
            'middleName': 'Middle name',
            'lastName': 'Last name',
            'birthDate': format_date(date.today() - timedelta(days=366 * 22)),
            'nationality': 'ae',
            'email': 'email@email.com',
            'phoneNumber': '+79992223344',
            'streetAddress': 'Street address',
            'apartment': '82',
            'postCode': '1234',
            'city': 'City',
            'country': 'ae',
            'passportNumber': '1234',
            'passportExpirationDate': format_date(date.today() + timedelta(days=30 * 2)),
            'passportDocument': str(KYCDocumentFactory(profile=profile).pk),
            'proofOfAddressDocument': str(KYCDocumentFactory(profile=profile).pk),
            'companyName': 'Company 1',
            'tradingName': 'Trademark 1',
            'placeOfIncorporation': 'Inc Place  1',
            'dateOfIncorporation': '2000-7-1',
            'commercialRegister': str(KYCDocumentFactory(profile=profile).pk),
            'shareholderRegister': str(KYCDocumentFactory(profile=profile).pk),
            'articlesOfIncorporation': str(KYCDocumentFactory(profile=profile).pk),
            'companyAddressRegistered': registered_address,
            'companyAddressPrincipal': principal_address,
            'beneficiaries': beneficiaries,
            'directors': directors,
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
        ([], {'step': 0}, 200),
        ([], {'step': 1}, 200),
        ([], {'step': 2}, 200),
        ([], {'step': 3}, 200),
        ([], {'step': 4}, 200),
        (['companyName'], {}, 400),
        (['tradingName'], {}, 400),
        (['dateOfIncorporation'], {}, 400),
        (['placeOfIncorporation'], {}, 400),
        (['companyAddressRegistered'], {'step': 1}, 400),
        ([], {'step': 1, 'companyAddressRegistered': {}}, 400),
        (['companyAddressPrincipal'], {'step': 1}, 200),
        (['firstName'], {'step': 2}, 400),
        (['lastName'], {'step': 2}, 400),
        (['middleName'], {'step': 2}, 200),
        (['birthDate'], {'step': 2}, 400),
        ([], {'step': 2, 'birthDate': format_date(date.today() - timedelta(days=366 * 18))}, 400),
        (['nationality'], {'step': 2}, 400),
        (['phoneNumber'], {'step': 2}, 400),
        ([], {'step': 2, 'phoneNumber': 'asdasdf'}, 400),
        (['email'], {'step': 2}, 400),
        (['streetAddress'], {'step': 2}, 400),
        (['apartment'], {'step': 2}, 200),
        (['city'], {'step': 2}, 400),
        (['postCode'], {'step': 2}, 200),
        (['country'], {'step': 2}, 400),
        (['passportNumber'], {'step': 2}, 400),
        (['passportExpirationDate'], {'step': 2}, 400),
        ([], {'step': 2, 'passportExpirationDate': format_date(date.today())}, 400),

        (['beneficiaries'], {'step': 3}, 400),
        ([], {'step': 3, 'beneficiaries': []}, 400),
        ([], {'step': 3, 'beneficiaries': [{'fullName': ''}]}, 400),

        (['directors'], {'step': 4}, 400),
        ([], {'step': 4, 'directors': []}, 400),
        ([], {'step': 4, 'directors': [{'fullName': ''}]}, 400),

        (['passportDocument'], {'step': 5}, 400),
        ([], {'step': 5, 'passportDocument': 'asd'}, 400),
        (['proofOfAddressDocument'], {'step': 5}, 400),
        (['commercialRegister'], {'step': 5}, 400),
        (['shareholderRegister'], {'step': 5}, 400),
        (['articlesOfIncorporation'], {'step': 5}, 400),
    )
)
@pytest.mark.django_db
def test_organization_kyc_validate(
    client,
    user_with_confirmed_phone,
    get_payload,
    remove_fields,
    overrides,
    expected_status_code,
):
    url = '/v1/kyc/organization/validate'
    client.force_login(user_with_confirmed_phone)
    response = client.post(
        url,
        get_payload(user_with_confirmed_phone.profile, *remove_fields, **overrides),
        content_type='application/json'
    )

    assert response.status_code == expected_status_code, response.content
    validate_response_schema(url, 'POST', response)
