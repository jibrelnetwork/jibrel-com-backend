import pytest

from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_view(client, full_verified_user, offering):
    client.force_login(full_verified_user)
    response = client.post(f'/v1/investment/offerings/{offering.pk}/application', {
        'amount': 1,
        'isAgreedRisks': True,
        'isAgreedSubscription': True,
    })
    assert response.status_code == 201
    validate_response_schema('/v1/investment/offerings/{offeringId}/application', 'POST', response)
