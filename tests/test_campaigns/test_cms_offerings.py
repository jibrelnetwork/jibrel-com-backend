import pytest
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import AuthenticationFailed

from tests.test_payments.utils import validate_response_schema


@pytest.mark.parametrize('key,exception', (
    ('123', AuthenticationFailed),
    (None, ImproperlyConfigured),
))
def test_auth(client, settings, key, exception):
    settings.CMS_INTEGRATION_PRIVATE_KEY = key
    with pytest.raises(exception):
        client.get(f'/cms/company/random/offerings')


@pytest.mark.django_db
def test_view(client, security, offering_factory, mocker):
    mocker.patch('jibrel.campaigns.views.CMSOfferingsAPIView.authenticate')

    response = client.get(f'/cms/company/{security.company.slug}/offerings')
    assert response.status_code == 200
    validate_response_schema('/cms/company/{companySlug}/offerings', 'GET', response)
    assert response.data == []

    offering_factory(security=security)

    response = client.get(f'/cms/company/{security.company.slug}/offerings')
    assert response.status_code == 200
    validate_response_schema('/cms/company/{companySlug}/offerings', 'GET', response)
    assert len(response.data) == 1

    offering = offering_factory()  # another security and company
    offering_factory(security=offering.security)

    response = client.get(f'/cms/company/{offering.security.company.slug}/offerings')
    assert response.status_code == 200
    validate_response_schema('/cms/company/{companySlug}/offerings', 'GET', response)
    assert len(response.data) == 2
