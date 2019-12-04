from datetime import date, timedelta

import pytest

from jibrel.authentication.factories import KYCDocumentFactory
from tests.test_payments.utils import validate_response_schema

from jibrel.kyc.models import OrganisationalKYCSubmission


def format_date(d: date):
    return d.strftime('%Y-%m-%d')


@pytest.fixture
def get_payload(db):
    def _get_payload(profile, *remove_fields, **overrides):
        company_info = {
            'companyName': 'Company 1',
            'tradingName': 'Trademark 1',
            'placeOfIncorporation': 'Inc Place  1',
            'dateOfIncorporation': '2000-7-1',
            'commercialRegister': str(KYCDocumentFactory(profile=profile).pk),
            'shareholderRegister': str(KYCDocumentFactory(profile=profile).pk),
            'articlesOfIncorporation': str(KYCDocumentFactory(profile=profile).pk),
        }

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
                'firstName': 'First name b one',
                'middleName': 'Middle name b one',
                'lastName': 'Last name b one',
                'birthDate': '1960-01-01',
                'nationality': 'ae',
                'email': 'b1@email.com',
                'streetAddress': 'Street address b1',
                'apartment': '111',
                'postCode': '1111',
                'city': 'City b1',
                'country': 'ae',
            },
            {
                'firstName': 'First name b two',
                'middleName': 'Middle name b two',
                'lastName': 'Last name b two',
                'birthDate': '1960-01-02',
                'nationality': 'ae',
                'email': 'b2@email.com',
                'streetAddress': 'Street address b2',
                'apartment': '222',
                'postCode': '2222',
                'city': 'City b2',
                'country': 'ae',
            },
        ]

        directors = [
            {
                'firstName': 'First name d one',
                'middleName': 'Middle name d one',
                'lastName': 'Last name d one',
            },
            {
                'firstName': 'First name d two',
                'middleName': 'Middle name d two',
                'lastName': 'Last name d two',
            },
        ]

        data = {
            'firstName': 'First name',
            'middleName': 'Middle name',
            'lastName': 'Last name',
            'birthDate': format_date(date.today() - timedelta(days=366 * 22)),
            'nationality': 'ae',
            'email': 'email@email.com',
            'streetAddress': 'Street address',
            'apartment': '82',
            'postCode': '1234',
            'city': 'City',
            'country': 'ae',
            'passportNumber': '1234',
            'passportExpirationDate': format_date(date.today() + timedelta(days=30 * 2)),
            'passportDocument': str(KYCDocumentFactory(profile=profile).pk),
            'proofOfAddressDocument': str(KYCDocumentFactory(profile=profile).pk),
            'companyInfo': company_info,
            'companyAddressRegistered': registered_address,
            'companyAddressPrincipal': principal_address,
            'beneficiaries': beneficiaries,
            'directors': directors,
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
        # (['middleName'], {}, 200),
        # (['apartment'], {}, 200),
        # (['postCode'], {}, 200),
        # (['occupation'], {'occupationOther': 'other'}, 200),
        # (['incomeSource'], {'incomeSourceOther': 'other'}, 200),
        #
        # (['occupation'], {}, 400),
        # (['incomeSource'], {}, 400),
        # ([], {'birthDate': format_date(date.today() - timedelta(days=366 * 18))}, 400),
        # ([], {'passportExpirationDate': format_date(date.today())}, 400),
        # ([], {'amlAgreed': False}, 400),
        # ([], {'uboConfirmed': False}, 400),
    )
)
@pytest.mark.django_db
def test_organization_kyc(
    client,
    user_with_confirmed_phone,
    get_payload,
    remove_fields,
    overrides,
    expected_status_code,
    mocker,
):
    url = '/v1/kyc/organization'
    onfido_mock = mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    client.force_login(user_with_confirmed_phone)

    payload = get_payload(user_with_confirmed_phone.profile, *remove_fields, **overrides)
    response = client.post(
        url,
        payload,
        content_type='application/json'
    )

    assert response.status_code == expected_status_code, response.content
    validate_response_schema(url, 'POST', response)
    if expected_status_code == 200:
        onfido_mock.assert_called()
    else:
        onfido_mock.assert_not_called()

    print(response.data)

    submission = OrganisationalKYCSubmission.objects.get(pk=response.data['data']['id'])

    print('S', submission)
    print('D', submission.directors.all())
    print('B', submission.beneficiaries.all())
    print('C', submission.company_info)
    assert True
