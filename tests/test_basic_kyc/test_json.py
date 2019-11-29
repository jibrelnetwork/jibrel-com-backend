from unittest.mock import call

import pytest

from jibrel.kyc.models import BasicKYCSubmission
from jibrel.kyc.serializers import BasicKYCSubmissionSerializer
from jibrel.kyc.forms.personal.v1 import PASSPORT, NATIONAL_ID

DATA = {
    'fullName': 'Karim Al Fazif',
    'alias': '',
    'birthDate': '',
    'birthDateHijri': '',
    'nationality': '',

    'address': '',
    'apartment': '',
    'city': '',
    'postcode': '',
    'country': '',

    'profession': '',
    'incomeSource': '',

    'personalIdType': '',
    'personalIdNumber': '',
    'personalIdDoe': '',
    'personalIdDoeHijri': '',
    'personalIdDocumentFront': '',
    'personalIdDocumentBack': '',
    'proofOfAddress': ''

}


@pytest.mark.django_db
@pytest.mark.parametrize('citizenship', BasicKYCSubmission.SUPPORTED_COUNTRIES)
def test_personal_payload(citizenship, user_with_phone):
    data = {
        **DATA,
        'nationality': citizenship,
        'country': citizenship
    }
    serializer = BasicKYCSubmissionSerializer(data=data, context={'profile': user_with_phone.profile})
    serializer.is_valid(raise_exception=False)
    assert serializer.errors == 0
