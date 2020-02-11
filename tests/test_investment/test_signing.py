import pytest

from django_banking.models import Asset
from jibrel.investment.docusign import DocuSignAPIException
from jibrel.investment.enum import (
    InvestmentApplicationAgreementStatus,
    InvestmentApplicationStatus
)
from jibrel.investment.models import SubscriptionAgreementTemplate
from jibrel.investment.tasks import docu_sign_start_task
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


@pytest.mark.parametrize(
    'status,exp_code1',
    (
        (InvestmentApplicationStatus.DRAFT, 200),
        (InvestmentApplicationStatus.PENDING, 409),
        (InvestmentApplicationStatus.HOLD, 409),
        (InvestmentApplicationStatus.COMPLETED, 409),
        (InvestmentApplicationStatus.CANCELED, 409),
        (InvestmentApplicationStatus.EXPIRED, 409),
        (InvestmentApplicationStatus.ERROR, 409),
    )
)
@pytest.mark.parametrize(
    'subscription_agreement_status,exp_code2',
    (
        (InvestmentApplicationAgreementStatus.INITIAL, 409),
        (InvestmentApplicationAgreementStatus.PREPARING, 409),
        (InvestmentApplicationAgreementStatus.PREPARED, 200),
        (InvestmentApplicationAgreementStatus.VALIDATING, 409),
        (InvestmentApplicationAgreementStatus.SUCCESS, 409),
        (InvestmentApplicationAgreementStatus.ERROR, 409),
    )
)
@pytest.mark.django_db
def test_finish_signing_api(
    client,
    full_verified_user,
    application_factory,
    status,
    subscription_agreement_status,
    exp_code1,
    exp_code2,
    mocker
):
    mock = mocker.patch('jibrel.investment.views.docu_sign_finish_task.delay')
    expected_status = max(exp_code1, exp_code2)
    client.force_login(full_verified_user)
    application = application_factory(status=status, subscription_agreement_status=subscription_agreement_status)
    response = client.post(f'/v1/investment/applications/{application.pk}/finish-signing')
    assert response.status_code == expected_status
    validate_response_schema('/v1/investment/applications/{applicationId}/finish-signing', 'POST', response)
    if expected_status == 200:
        mock.assert_called()


@pytest.mark.django_db
def test_start_signing_task(application_factory, subscription_agreement_template_factory, mocker):
    mocker.patch('jibrel.investment.docusign.DocuSignAPI.authenticate')
    application = application_factory(
        status=InvestmentApplicationStatus.DRAFT,
        subscription_agreement_status=InvestmentApplicationAgreementStatus.INITIAL,
    )

    with pytest.raises(SubscriptionAgreementTemplate.DoesNotExist):
        docu_sign_start_task(str(application.pk))
    application.refresh_from_db()
    assert application.subscription_agreement_status == InvestmentApplicationAgreementStatus.ERROR

    application.subscription_agreement_status = InvestmentApplicationAgreementStatus.INITIAL
    application.save()
    subscription_agreement_template_factory(application.offering)

    mocker.patch(
        'jibrel.investment.tasks.DocuSignAPI.create_envelope',
        side_effect=DocuSignAPIException
    )
    with pytest.raises(DocuSignAPIException):
        docu_sign_start_task(str(application.pk))
    application.refresh_from_db()
    assert application.subscription_agreement_status == InvestmentApplicationAgreementStatus.ERROR
