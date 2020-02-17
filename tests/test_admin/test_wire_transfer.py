import pytest
from django.urls import reverse

from django_banking.contrib.wire_transfer.models import (
    ColdBankAccount,
    DepositWireTransferOperation,
    RefundWireTransferOperation
)
from django_banking.models import Asset
from django_banking.models.assets.enum import AssetType
from django_banking.models.transactions.enum import OperationStatus


@pytest.mark.django_db
def test_cold_bank_account_view(admin_client, cold_bank_account_factory):
    obj = cold_bank_account_factory()
    model = ColdBankAccount
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_deposit_wire_transfer_view(admin_client, full_verified_user, create_deposit_operation, asset_usd):
    obj = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17
    )
    model = DepositWireTransferOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200

@pytest.mark.parametrize(
    'tool,status',
    (
        ('commit', OperationStatus.COMMITTED),
        ('cancel', OperationStatus.CANCELLED),
    )
)
@pytest.mark.django_db
def test_deposit_wire_transfer_commit_cancel(admin_client, full_verified_user, create_deposit_operation, asset_usd, tool, status, mocker):
    email_mock = mocker.patch('jibrel.payments.signals.handler.email_message_send')
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17,
        commit=False
    )
    assert deposit.status == OperationStatus.HOLD
    model = DepositWireTransferOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
            'pk': deposit.pk,
            'tool': tool
        })
    response = admin_client.get(url)
    assert response.status_code == 302
    deposit.refresh_from_db()
    assert deposit.status == status
    email_mock.assert_called()


@pytest.mark.django_db
def test_refund_wire_transfer_view(admin_client, full_verified_user, create_deposit_operation, create_refund_operation, asset_usd):
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17
    )
    obj = create_refund_operation(
        amount=17,
        deposit=deposit
    )
    model = RefundWireTransferOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_refund_wire_transfer_action(admin_client, full_verified_user, create_deposit_operation, asset_usd):
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17
    )
    model = DepositWireTransferOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
            'pk': deposit.pk,
            'tool': 'refund'
        })

    response = admin_client.post(url)
    assert response.status_code == 200
