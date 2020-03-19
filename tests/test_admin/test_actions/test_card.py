import pytest
from django.urls import reverse

from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge
from django_banking.contrib.card.models import DepositCardOperation
from django_banking.models.transactions.enum import (
    OperationMethod,
    OperationStatus
)
from jibrel.investment.enum import InvestmentApplicationStatus


@pytest.mark.parametrize(
    'create_application',
    (
        True, False
    )
)
@pytest.mark.django_db
def test_refund_card_action(admin_client, full_verified_user, create_deposit_operation, asset_usd, application_factory,
                            create_application,
                            ):
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17,
        method=OperationMethod.CARD,
        references={
            'card_account': {
                'type': 'foloosi'
            }
        }
    )
    FoloosiCharge.objects.create(
        full_verified_user,
        deposit,
        payment={
            "reference_token": "reference_token"
        }
    )
    if create_application:
        application = application_factory(status=InvestmentApplicationStatus.HOLD)
        application.deposit = deposit
        application.save()

    model = DepositCardOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
            'pk': deposit.pk,
            'tool': 'refund'
        })

    response = admin_client.post(url, {'confirm': 'yes'})
    assert response.status_code == 302
    deposit.refresh_from_db()
    assert deposit.status == OperationStatus.COMMITTED
    assert deposit.refund.status == OperationStatus.COMMITTED
    if create_application:
        application.refresh_from_db()
        assert application.status == InvestmentApplicationStatus.CANCELED
