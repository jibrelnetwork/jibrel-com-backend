import pytest
from django.urls import reverse

from django_banking.contrib.wire_transfer.models import (
    ColdBankAccount,
    DepositWireTransferOperation,
    RefundWireTransferOperation
)
from django_banking.models import Asset
from django_banking.models.assets.enum import AssetType


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


@pytest.mark.django_db
def test_deposit_wire_transfer_commit(admin_client, full_verified_user, create_deposit_operation):
    pass


@pytest.mark.django_db
def test_deposit_wire_transfer_cancel(admin_client, full_verified_user, create_deposit_operation):
    pass


@pytest.mark.django_db
def test_refund_wire_transfer_view(admin_client, full_verified_user, create_refund_operation, asset_usd):
    obj = create_refund_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17
    )
    model = RefundWireTransferOperation
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
