import itertools as _it
from datetime import date, timedelta

import pytest
from django.core.files.base import ContentFile

from jibrel.kyc.models import BasicKYCSubmission, Document
from jibrel.kyc.services import upload_document

SOME_TEXT = 'some text 123'

BOOL_FIELD_VALUES = (True, False)
HIJRI_FIELD_VALUES = ('', SOME_TEXT,)
PAST_ISO_FIELD_VALUES = ('', date(1993, 12, 10))
FUTURE_ISO_FIELD_VALUES = (
    '',
    date.today() + timedelta(days=BasicKYCSubmission.MIN_DAYS_TO_EXPIRATION + 1)
)

BIRTHDATE = 'birthDate'
PERSONAL_ID_DOE = 'personalIdDoe'
RESIDENCY_VISA_DOE = 'residencyVisaDoe'
PAST_ISO_FIELDS = (BIRTHDATE,)
FUTURE_ISO_FIELDS = (PERSONAL_ID_DOE, RESIDENCY_VISA_DOE,)

CONDITION_FIELDS_MAP = {
    'isBirthDateHijri': 'is_birth_date_hijri',
    'isPersonalIdDoeHijri': 'is_personal_id_doe_hijri',
    'isResidencyVisaDoeHijri': 'is_residency_visa_doe_hijri'
}
HIJRI_FIELDS_MAP = {
    'birthDateHijri': 'birth_date_hijri',
    'personalIdDoeHijri': 'personal_id_doe_hijri',
    'residencyVisaDoeHijri': 'residency_visa_doe_hijri'}
ISO_FIELDS_MAP = {
    BIRTHDATE: 'birth_date',
    PERSONAL_ID_DOE: 'personal_id_doe',
    RESIDENCY_VISA_DOE: 'residency_visa_doe'
}


def _upload_document(profile, doc_type, side=Document.FRONT_SIDE):
    return str(upload_document(
        file=ContentFile(b'some_file_content'),
        type=doc_type,
        side=side,
        profile=profile
    ))


@pytest.mark.urls('jibrel.kyc.urls')
@pytest.mark.django_db
@pytest.mark.parametrize(
    'ternary_fields',
    (
        _it.product(
            _it.product(
                (condition_field,),
                BOOL_FIELD_VALUES
            ),
            _it.product(
                _it.product(
                    (hijri_field,),
                    HIJRI_FIELD_VALUES
                ),
                _it.product(
                    (iso_fields,),
                    (
                        PAST_ISO_FIELD_VALUES
                        if BIRTHDATE in iso_fields else
                        FUTURE_ISO_FIELD_VALUES
                    )
                )
            )
        )
        for condition_field, hijri_field, iso_fields in zip(
            CONDITION_FIELDS_MAP, HIJRI_FIELDS_MAP, ISO_FIELDS_MAP
        )
    )
)
def test_basic_kyc_hijri(
    client,
    user_with_confirmed_phone,
    ternary_fields,
    mocker
):
    mocker.patch('jibrel.kyc.services.enqueue_onfido_routine')
    mocker.patch('jibrel.kyc.views.send_kyc_submitted_email')
    client.force_login(user_with_confirmed_phone)
    basic_data = {
        "firstName": "Karim Al Fazif",
        "middleName": "Karim Al Fazif",
        "lastName": "Karim Al Fazif",
        "nationality": "AE",
        "primaryPhone": {},
        "email": {},
        "streetAddress": "asdasd, 36",
        "apartment": "321",
        "city": "asdasd",
        "country": "AE",
        "occupation": "cacs",
        "incomeSource": "dsasd",
        "amlAgreed": True,
        "uboConfirmed": True,
        "postCode": "456456",
        'birthDateHijri': SOME_TEXT,
        'personalIdType': Document.NATIONAL_ID,
        'personalIdDoeHijri': SOME_TEXT,
        'personalIdNumber': '123123',
        'residencyVisaNumber': '123123',
        'personalIdDocumentFront': _upload_document(
            user_with_confirmed_phone.profile,
            Document.NATIONAL_ID
        ),
        'personalIdDocumentBack': _upload_document(
            user_with_confirmed_phone.profile,
            Document.NATIONAL_ID,
            side=Document.BACK_SIDE
        ),
        'proofOfAddress': _upload_document(
            user_with_confirmed_phone.profile,
            Document.PROOF_OF_ADDRESS
        ),
        'isBirthDateHijri': True,
        'isPersonalIdDoeHijri': True,
    }
    for (
            (condition_field, condition_value),
            (
                (hijri_field, hijri_value),
                (iso_field, iso_value)
            )
    ) in ternary_fields:
        basic_data.update({
            condition_field: condition_value,
            hijri_field: hijri_value,
            iso_field: iso_value
        })
        response = client.post(
            '/personal',
            basic_data
        )
        if condition_value and not hijri_value:
            assert response.status_code == 400
            assert hijri_field in [v['target'] for v in response.data['errors']]
        elif not condition_value and not iso_value:
            assert response.status_code == 400
            assert iso_field in [v['target'] for v in response.data['errors']]
        else:
            assert response.status_code == 200

            added_kyc = BasicKYCSubmission.objects.get(pk=response.data['data']['id'])
            assert getattr(added_kyc, CONDITION_FIELDS_MAP.get(condition_field)) == condition_value
            if condition_value:
                assert getattr(added_kyc, HIJRI_FIELDS_MAP.get(hijri_field)) == hijri_value
                assert getattr(added_kyc, ISO_FIELDS_MAP.get(iso_field)) is None
            else:
                assert getattr(added_kyc, ISO_FIELDS_MAP.get(iso_field)) == iso_value
                assert getattr(added_kyc, HIJRI_FIELDS_MAP.get(hijri_field)) is None
            added_kyc.delete()
