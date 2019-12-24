import io
from datetime import (
    date,
    timedelta
)

import pytest

from jibrel.authentication.factories import KYCDocumentFactoryWithFileField
from jibrel.kyc import (
    models,
    tasks
)


def format_date(d: date):
    return d.strftime('%Y-%m-%d')


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://redis/0',
        'result_backend': 'redis://redis/0',
    }


@pytest.mark.django_db(transaction=True)
def test_enqueue_onfido_routine(celery_worker, user_not_confirmed, mocker):
    profile = user_not_confirmed.profile
    onfido_mock = mocker.patch('jibrel.kyc.tasks.onfido_api')

    file_mock = mocker.patch('jibrel.core.storages.AmazonS3Storage.save')
    file_mock2 = mocker.patch('jibrel.core.storages.AmazonS3Storage.open')
    file_mock.return_value = 'abc.pdf'
    file_mock2.return_value = io.BytesIO()

    data = {
            'first_name': 'First name',
            'middle_name': 'Middle name',
            'last_name': 'Last name',
            'birth_date': (date.today() - timedelta(days=366 * 22)),
            'nationality': 'ae',
            'street_address': 'Street address',
            'apartment': '82',
            'post_code': '1234',
            'city': 'City',
            'country': 'ae',
            'occupation': 'marketing',
            'income_source': 'sale_assets',
            'passport_number': '1234',
            'passport_expiration_date': (date.today() + timedelta(days=30 * 2)),
            'passport_document': KYCDocumentFactoryWithFileField(profile=profile),
            'proof_of_address_document': KYCDocumentFactoryWithFileField(profile=profile),
            'is_agreed_risks': True,
            'profile': profile
        }
    submission = models.IndividualKYCSubmission.objects.create(**data)
    onfido_mock.create_applicant.return_value = 'AAA-001'
    onfido_mock.create_check.return_value = 'C1'
    m = mocker.Mock()
    m.status = 'complete'
    m.result = 'consider'
    m.download_uri = 'report'
    onfido_mock.get_check_results.return_value = m
    onfido_mock.download_report.return_value = b'report data'

    res = tasks.enqueue_onfido_routine(submission)
    res.get()

    onfido_mock.create_applicant.assert_called_with(**{
        'birth_date': data['birth_date'],
        'country': 'ARE',
        'email': user_not_confirmed.email,
        'first_name': 'First name',
        'last_name': 'Last name',
        'middle_name': 'Middle name'
    })
    onfido_mock.create_check.assert_called_with(applicant_id='AAA-001')
    onfido_mock.get_check_results.assert_called_with(applicant_id='AAA-001', check_id='C1')
    onfido_mock.download_report.assert_called_with('report.pdf')
    onfido_mock.upload_document.assert_called_with(**{
        'applicant_id': 'AAA-001',
        'country': 'ARE',
        'document_type': 'passport',
        'file_path': mocker.ANY
    })
    submission = models.IndividualKYCSubmission.objects.get(pk=submission.pk)
    assert submission.onfido_applicant_id == 'AAA-001'
    assert submission.onfido_check_id == 'C1'
    assert submission.onfido_result == 'consider'
    assert submission.onfido_report == 'abc.pdf'
