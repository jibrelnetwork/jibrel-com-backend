from copy import deepcopy

import pytest
from django.test import override_settings
from django.urls import reverse

from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus
from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge
from django_banking.contrib.card.models import DepositCardOperation
from django_banking.models.transactions.enum import (
    OperationMethod,
    OperationStatus
)
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.payments.tasks import (
    checkout_refund,
    checkout_request,
    checkout_update
)


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
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


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_refund_checkout_action(admin_client, full_verified_user, create_deposit_operation, asset_usd,
                                checkout_base_stub, checkout_stub, mocker):
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17,
        method=OperationMethod.CARD,
        references={
            'card_account': {
                'type': 'checkout'
            }
        }
    )
    stubs = [
        checkout_stub(
            full_verified_user, deposit.amount,
            deposit=deposit,
            status=CheckoutStatus.CAPTURED
        ),
        checkout_base_stub({
            "action_id": "act_y3oqhf46pyzuxjbcn2giaqnb44",
            "reference": "ORD-5023-4E89",
        })
    ]
    mock = mocker.patch('checkout_sdk.checkout_api.PaymentsClient._send_http_request', side_effect=stubs)
    refund_task = mocker.patch('jibrel.payments.tasks.checkout_refund.delay', side_effect=checkout_refund)
    checkout_request(
        deposit_id=deposit.pk,
        user_id=full_verified_user.pk,
        amount=deposit.amount,
        reference_code=deposit.references['reference_code'],
        checkout_token='checkout_token'
    )
    assert deposit.status == OperationStatus.COMMITTED
    assert deposit.refund is None

    model = DepositCardOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
                  kwargs={
                      'pk': deposit.pk,
                      'tool': 'refund'
                  })

    response = admin_client.post(url, {'confirm': 'yes'})
    assert response.status_code == 302
    # now we should get webhook
    refund_task.assert_called()
    # should called twice. first time at install and the second time at request refund
    assert mock.call_count == 2
