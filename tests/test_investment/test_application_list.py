import pytest

from jibrel.investment.enum import InvestmentApplicationStatus
from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_applications_list(client, application_factory, full_verified_user):
    client.force_login(full_verified_user)
    url = '/v1/investment/applications'

    total = 2
    amount = 17

    for i in range(total):
        application_factory(amount)

    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data['data']) == total
    validate_response_schema(url, 'get', response)


@pytest.mark.django_db
def test_offerings_summary(client, application_factory, full_verified_user):
    client.force_login(full_verified_user)
    url = '/v1/investment/offerings/summary'

    application_factory()
    application_factory(status=InvestmentApplicationStatus.CANCELED)
    application_factory(status=InvestmentApplicationStatus.PENDING)
    application_factory(status=InvestmentApplicationStatus.HOLD)

    response = client.get(url)
    assert response.status_code == 200
    assert response.data['total_investment'] == f'34.00'
    validate_response_schema(url, 'get', response)
