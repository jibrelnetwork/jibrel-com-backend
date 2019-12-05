import json
from datetime import date, datetime, timedelta

import pytest

from jibrel.authentication.factories import KYCDocumentFactory
from jibrel.kyc.models import OrganisationalKYCSubmission
from tests.test_payments.utils import validate_response_schema

DATE_FORMAT = '%Y-%m-%d'


def format_date(d: date):
    return d.strftime(DATE_FORMAT)


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


@pytest.mark.django_db
def test_organization_kyc_ok(
    client,
    user_with_confirmed_phone,
    get_payload,
    mocker,
):
    url = '/v1/kyc/organization'
    onfido_mock = mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    client.force_login(user_with_confirmed_phone)

    payload = get_payload(user_with_confirmed_phone.profile)
    response = client.post(
        url,
        payload,
        content_type='application/json'
    )

    assert response.status_code == 200
    validate_response_schema(url, 'POST', response)
    onfido_mock.assert_called()

    # onfido_mock.assert_not_called()

    submission = OrganisationalKYCSubmission.objects.get(pk=response.data['data']['id'])

    assert submission.profile == user_with_confirmed_phone.profile

    assert submission.first_name == payload['firstName']
    assert submission.last_name == payload['lastName']
    assert submission.middle_name == payload['middleName']
    assert submission.birth_date == datetime.strptime(payload['birthDate'], DATE_FORMAT).date()
    assert submission.nationality == payload['nationality'].upper()
    assert submission.email == payload['email']
    assert submission.street_address == payload['streetAddress']
    assert submission.apartment == payload['apartment']
    assert submission.post_code == payload['postCode']
    assert submission.city == payload['city']
    assert submission.country == payload['country'].upper()
    assert submission.passport_number == payload['passportNumber']
    assert submission.passport_expiration_date == datetime.strptime(
        payload['passportExpirationDate'], DATE_FORMAT).date()
    assert str(submission.passport_document.pk) == payload['passportDocument']
    assert str(submission.proof_of_address_document.pk) == payload['proofOfAddressDocument']

    for i, d in enumerate(submission.directors.order_by('pk').all()):
        pd = payload['directors'][i]
        assert d.first_name == pd['firstName']
        assert d.last_name == pd['lastName']
        assert d.middle_name == pd['middleName']

    for i, b in enumerate(submission.beneficiaries.order_by('pk').all()):
        pb = payload['beneficiaries'][i]
        assert b.first_name == pb['firstName']
        assert b.last_name == pb['lastName']
        assert b.middle_name == pb['middleName']
        assert b.birth_date == datetime.strptime(pb['birthDate'], DATE_FORMAT).date()
        assert b.nationality == pb['nationality'].upper()
        assert b.email == pb['email']
        assert b.street_address == pb['streetAddress']
        assert b.apartment == pb['apartment']
        assert b.post_code == pb['postCode']
        assert b.city == pb['city']
        assert b.country == pb['country'].upper()

    ci = payload['companyInfo']
    assert submission.company_info.company_name == ci['companyName']
    assert submission.company_info.trading_name == ci['tradingName']
    assert submission.company_info.place_of_incorporation == ci['placeOfIncorporation']
    assert submission.company_info.date_of_incorporation == datetime.strptime(
        ci['dateOfIncorporation'], DATE_FORMAT).date()
    assert str(submission.company_info.commercial_register.pk) == ci['commercialRegister']
    assert str(submission.company_info.shareholder_register.pk) == ci['shareholderRegister']
    assert str(submission.company_info.articles_of_incorporation.pk) == ci['articlesOfIncorporation']


@pytest.mark.django_db
def test_organization_kyc_miss_all_required(
    client,
    user_with_confirmed_phone,
    mocker,
):
    url = '/v1/kyc/organization'
    onfido_mock = mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    client.force_login(user_with_confirmed_phone)

    response = client.post(
        url,
        {},
        content_type='application/json'
    )

    assert response.status_code == 400
    validate_response_schema(url, 'POST', response)
    onfido_mock.assert_not_called()

    errors = response.data['errors']
    required_error = [{'code': 'required', 'message': 'This field is required.'}]
    assert errors == {
        'beneficiaries': required_error,
        'birthDate': required_error,
        'city': required_error,
        'companyAddressPrincipal': required_error,
        'companyAddressRegistered': required_error,
        'companyInfo': required_error,
        'country': required_error,
        'directors': required_error,
        'email': required_error,
        'firstName': required_error,
        'lastName': required_error,
        'nationality': required_error,
        'passportDocument': required_error,
        'passportExpirationDate': required_error,
        'passportNumber': required_error,
        'proofOfAddressDocument': required_error,
        'streetAddress': required_error
    }


@pytest.mark.django_db
def test_organization_kyc_miss_nested_fields_required(
    client,
    user_with_confirmed_phone,
    get_payload,
    mocker,
):
    url = '/v1/kyc/organization'
    onfido_mock = mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    client.force_login(user_with_confirmed_phone)
    payload = get_payload(
        user_with_confirmed_phone.profile,
        companyInfo={},
        companyAddressPrincipal={},
        companyAddressRegistered={},
        beneficiaries=[{}],
        directors=[{}]
    )
    response = client.post(
        url,
        payload,
        content_type='application/json'
    )

    assert response.status_code == 400
    # validate_response_schema(url, 'POST', response)  # TODO: describe nested errors in swagger.yml
    onfido_mock.assert_not_called()

    errors = response.data['errors']
    required_error = [{'code': 'required', 'message': 'This field is required.'}]
    assert errors == {'beneficiaries': [{'birthDate': required_error,
                                         'city': required_error,
                                         'country': required_error,
                                         'email': required_error,
                                         'firstName': required_error,
                                         'lastName': required_error,
                                         'nationality': required_error,
                                         'streetAddress': required_error}],
                      'companyAddressPrincipal': {'city': required_error,
                                                  'country': required_error,
                                                  'streetAddress': required_error},
                      'companyAddressRegistered': {'city': required_error,
                                                   'country': required_error,
                                                   'streetAddress': required_error},
                      'companyInfo': {'articlesOfIncorporation': required_error,
                                      'commercialRegister': required_error,
                                      'dateOfIncorporation': required_error,
                                      'shareholderRegister': required_error},
                      'directors': [{'firstName': required_error,
                                     'lastName': required_error}]}
