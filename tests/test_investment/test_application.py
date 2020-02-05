import pytest

from django_banking.contrib.wire_transfer.models import ColdBankAccount
from django_banking.models import Asset
from jibrel.core.errors import ServiceUnavailableException
from tests.test_banking.factories.wire_transfer import ColdBankAccountFactory
from tests.test_payments.utils import validate_response_schema


def apply_offering(client, offering):
    return client.post(f'/v1/investment/offerings/{offering.pk}/application', {
        'amount': 1,
        'isAgreedRisks': True,
        'isAgreedSubscription': True
    })


@pytest.mark.django_db
def test_application_cold_bank_account_missing(client, full_verified_user, offering, mocker):
    def handle_exc(self, exc):
        raise exc
    mocker.patch('jibrel.investment.views.InvestmentApplicationAPIView.handle_exception', handle_exc)
    mocker.patch('jibrel.investment.views.email_message_send')

    client.force_login(full_verified_user)
    mock = mocker.patch('jibrel.investment.views.ColdBankAccount.objects.for_customer')
    mock.side_effect = ColdBankAccount.DoesNotExist()
    with pytest.raises(ServiceUnavailableException):
        apply_offering(client, offering)


@pytest.mark.django_db
def test_application_api(client, full_verified_user, offering, mocker):
    mocker.patch('jibrel.investment.views.email_message_send')
    ColdBankAccountFactory.create(account__asset=Asset.objects.main_fiat_for_customer(full_verified_user))

    client.force_login(full_verified_user)

    response = apply_offering(client, offering)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/offerings/{offeringId}/application', 'POST', response)

    response = apply_offering(client, offering)
    assert response.status_code == 409
    validate_response_schema('/v1/investment/offerings/{offeringId}/application', 'POST', response)


@pytest.mark.django_db
def test_personal_agreements(client, full_verified_user, offering, personal_agreement_factory, mocker):
    mocker.patch('jibrel.investment.views.email_message_send')
    ColdBankAccountFactory.create(account__asset=Asset.objects.main_fiat_for_customer(full_verified_user))
    personal_agreement = personal_agreement_factory(offering, full_verified_user)
    client.force_login(full_verified_user)

    assert personal_agreement.is_agreed is False
    response = apply_offering(client, offering)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/offerings/{offeringId}/application', 'POST', response)

    personal_agreement.refresh_from_db()
    assert personal_agreement.is_agreed is True


@pytest.mark.django_db
def test_personal_agreements_get(settings, client, full_verified_user, offering, personal_agreement_factory, mocker):
    mocker.patch('jibrel.core.storages.AmazonS3Storage.url', return_value='test')


    url = f'/v1/investment/offerings/{offering.pk}/agreement'
    response = client.get(url)
    assert response.status_code == 403

    agreement_url = f'http://{settings.DOMAIN_NAME.rstrip("/")}/docs/en/subscription-agreement-template.pdf'
    client.force_login(full_verified_user)
    response = client.get(url)

    assert response.status_code == 302
    assert response['Location'] == agreement_url

    personal_agreement_factory(offering, full_verified_user)
    response = client.get(url)
    assert response.status_code == 302
    assert response['Location'] == 'test'
    validate_response_schema('/v1/investment/offerings/{offeringId}/agreement', 'GET', response)

    url = f'/v1/investment/offerings/blabla/agreement'
    response = client.get(url)
    assert response.status_code == 404
