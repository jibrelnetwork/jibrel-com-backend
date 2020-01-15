import pytest

from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_auth(client, full_verified_user):
    url = '/v1/campaigns/company/random/offerings'
    response = client.get(url)
    assert response.status_code == 403

    client.force_login(full_verified_user)
    response = client.get(f'/v1/campaigns/company/random/offerings')
    assert response.status_code == 200
    validate_response_schema('/v1/campaigns/company/{companySlug}/offerings', 'GET', response)
