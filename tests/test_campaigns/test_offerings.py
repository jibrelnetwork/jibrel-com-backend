import pytest
from rest_framework.exceptions import NotAuthenticated

from tests.test_payments.utils import validate_response_schema


def test_auth(client, mocker):
    def handle_exc(self, exc):
        raise exc
    mocker.patch('jibrel.campaigns.views.CMSOfferingsAPIView.handle_exception', handle_exc)
    with pytest.raises(NotAuthenticated):
        client.get(f'/v1/campaigns/company/random/offerings')


@pytest.mark.django_db
def test_view(client, full_verified_user, security, offering_factory, mocker):
    client.force_login(full_verified_user)
    response = client.get(f'/v1/campaigns/company/{security.company.slug}/offerings')
    assert response.status_code == 200
    validate_response_schema('/v1/campaigns/company/{companySlug}/offerings', 'GET', response)
