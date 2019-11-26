from unittest.mock import call

import pytest

from jibrel.kyc.models import BasicKYCSubmission
from jibrel.kyc.serializers import PersonalIdTypeValidator


@pytest.mark.parametrize('citizenship', BasicKYCSubmission.SUPPORTED_COUNTRIES)
def test_national_id_supported_citizenship(citizenship, mocker):
    validator = PersonalIdTypeValidator()
    mocked = mocker.patch.object(validator, 'add_error')
    validator({
        'personalIdType': BasicKYCSubmission.NATIONAL_ID,
        'citizenship': citizenship,
        'residency': citizenship,
    })
    mocked.assert_not_called()


@pytest.mark.parametrize('citizenship', ('AU', 'IQ', 'KG', 'LU', 'US'))
def test_national_id_not_supported_citizenship(citizenship, mocker):
    validator = PersonalIdTypeValidator()
    mocked = mocker.patch.object(validator, 'add_error')
    validator({
        'personalIdType': BasicKYCSubmission.NATIONAL_ID,
        'citizenship': citizenship,
        'residency': next(iter(BasicKYCSubmission.SUPPORTED_COUNTRIES)),
    })
    mocked.assert_called_with('personalIdType', 'invalid')


@pytest.mark.parametrize('residency', BasicKYCSubmission.SUPPORTED_COUNTRIES)
def test_passport_supported_residency(residency, mocker):
    validator = PersonalIdTypeValidator()
    mocked = mocker.patch.object(validator, 'add_error')
    validator({
        'personalIdType': BasicKYCSubmission.PASSPORT,
        'citizenship': 'RU',
        'residency': residency,
    })
    mocked.assert_not_called()


def test_passport_not_supported_residency(mocker):
    validator = PersonalIdTypeValidator()
    mocked = mocker.patch.object(validator, 'add_error')
    validator({
        'personalIdType': BasicKYCSubmission.PASSPORT,
        'citizenship': 'RU',
        'residency': 'US',
    })
    mocked.assert_has_calls(
        (call('citizenship', 'invalid'), call('residency', 'invalid')),
        any_order=True,
    )
