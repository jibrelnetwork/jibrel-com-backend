from datetime import timedelta

import pytest
from django.utils import timezone

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.models import InvestmentApplication
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
def test_active_offerings(client, security, full_verified_user, offering_factory, mocker):
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
    response = client.get(url)
    assert response.status_code == 200

    # TODO factory
    asset = Asset.objects.create(name='Tmp', symbol='XYZ')
    acc1 = Account.objects.create(type=AccountType.TYPE_ACTIVE, strict=True, asset=asset)
    InvestmentApplication.objects.create(
        offering=offering,
        user=full_verified_user,
        account=acc1,
        amount=10
    )
    response = client.get(url)
    assert response.status_code == 409
