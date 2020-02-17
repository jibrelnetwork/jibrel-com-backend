from datetime import timedelta

import pytest
from django.utils import timezone

from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.enum import InvestmentApplicationStatus
from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_auth(client, full_verified_user):
    url = '/v1/campaigns/company/random/offerings'
    response = client.get(url)
    assert response.status_code == 403

    client.force_login(full_verified_user)
    response = client.get(url)
    assert response.status_code == 200
    validate_response_schema('/v1/campaigns/company/{companySlug}/offerings', 'GET', response)


@pytest.mark.django_db
def test_active_offerings(client, security_factory, full_verified_user, offering_factory, application_factory):
    security = security_factory()

    url = f'/v1/campaigns/company/{security.company.slug}/offerings/active'
    client.force_login(full_verified_user)
    response = client.get(url)
    assert response.status_code == 404

    offering = offering_factory(
        security=security,
        status=OfferingStatus.ACTIVE,
        date_start=timezone.now() - timedelta(1),
        date_end=timezone.now() + timedelta(1)
    )

    security2 = security_factory()
    offering_factory(
        security=security2,
        status=OfferingStatus.ACTIVE,
        date_start=timezone.now() - timedelta(1),
        date_end=timezone.now() + timedelta(1)
    )

    response = client.get(url)
    assert response.status_code == 200

    application_factory(offering=offering, user=full_verified_user, status=InvestmentApplicationStatus.PENDING)
    response = client.get(url)
    assert response.status_code == 409

    url = f'/v1/campaigns/company/{security2.company.slug}/offerings/active'
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_application_api(client, full_verified_user, offering, mocker):
    url = f'/v1/investment/offerings/{offering.pk}'
    response = client.get(url)
    assert response.status_code == 403
    client.force_login(full_verified_user)
    response = client.get(url)
    assert response.status_code == 200
    validate_response_schema('/v1/investment/offerings/{offeringId}', 'GET', response)
