import pytest
from django.contrib import admin
from django.urls import reverse

from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation,
    RefundWireTransferOperation
)
from jibrel.authentication.models import OneTimeToken
from jibrel.investment.models import InvestmentApplication
from jibrel.notifications.models import ExternalServiceCallLog
from jibrel.wallets.models import Wallet

APP_ALL = set(admin.site._registry.keys())
APP_ADD_RESTRICTED = {
    OneTimeToken,
    ExternalServiceCallLog,
    DepositWireTransferOperation,
    RefundWireTransferOperation,
    InvestmentApplication,
    Wallet
}
APP_ADD_ALLOWED = APP_ALL - APP_ADD_RESTRICTED


@pytest.mark.parametrize(
    'url',
    [
        *(
            reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add')
            for model in APP_ADD_ALLOWED
        )
    ]
)
@pytest.mark.django_db
def test_add_page(admin_client, url):
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    'url',
    [
        *(
            reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add')
            for model in APP_ADD_RESTRICTED
        )
    ]
)
@pytest.mark.django_db
def test_add_page_restricted(admin_client, url):
    response = admin_client.get(url)
    assert response.status_code == 403
