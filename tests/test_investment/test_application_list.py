from datetime import timedelta

import pytest
from django.utils import timezone

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import InvestmentApplication
from tests.test_payments.utils import validate_response_schema


@pytest.mark.django_db
def test_view(client, full_verified_user, offering):
    client.force_login(full_verified_user)
    response = client.get(f'/v1/investment/offerings')
    assert response.status_code == 200


@pytest.mark.django_db
def test_offerings_list(client, security_factory, full_verified_user, offering_factory, offering):
    client.force_login(full_verified_user)
    url = '/v1/investment/offerings'

    total = 2
    for i in range(total):
        security = security_factory()
        offering = offering_factory(
            security=security,
            status=OfferingStatus.ACTIVE,
            date_start=timezone.now() - timedelta(1),
            date_end=timezone.now() + timedelta(1)
        )

        asset = Asset.objects.create(name=f'Tmp{i}', symbol=f'XY{i}')
        acc1 = Account.objects.create(type=AccountType.TYPE_ACTIVE, strict=True, asset=asset)
        InvestmentApplication.objects.create(
            offering=offering,
            user=full_verified_user,
            account=acc1,
            amount=17,
            is_agreed_risks=True,
            is_agreed_subscription=True,
            status=InvestmentApplicationStatus.COMPLETED
        )

    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data['data']) == total
    assert response.data['total_investment'] == f'{total * 17}.00'
    validate_response_schema(url, 'get', response)
