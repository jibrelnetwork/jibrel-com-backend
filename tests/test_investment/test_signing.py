import pytest

from django_banking.models import Asset
from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_create_application_calls_docusign(client, full_verified_user, offering, mocker, cold_bank_account_factory):
    mock = mocker.patch('jibrel.investment.views.docu_sign_start_task.delay')
    cold_bank_account_factory(Asset.objects.main_fiat_for_customer(full_verified_user))
    client.force_login(full_verified_user)
    response = client.post(
        f'/v1/investment/offerings/{offering.pk}/application',
        {
            'amount': 0,
            'isAgreedRisks': True,
        }
    )
    assert response.status_code == 201, response.data
    validate_response_schema('/v1/investment/offerings/{offeringId}/application', 'POST', response)
    mock.assert_called()
