import pytest
from django.urls import reverse

from django_banking.contrib.wire_transfer.models import ColdBankAccount
from django_banking.models import UserAccount
from jibrel.investment.models import InvestmentApplication


def create_investment_deposit(admin_client, application, amount):
    model = InvestmentApplication
    url = reverse(
        f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
            'pk': application.pk,
            'tool': 'add_payment'
        }
    )
    response = admin_client.post(url, {
        'swift_code': 'ADCBAEAATRY',
        'bank_name': 'ABU DHABI COMMERCIAL BANK',
        'holder_name': 'Mehdi Dehbi',
        'iban_number': 'SA0380000000608010167519',
        'amount': amount
    })
    return response


@pytest.mark.django_db
def test_investment_application_deposit(admin_client, asset_usd, cold_bank_account_factory, application_factory):
    cold_bank_account_factory(asset=asset_usd)
    application = application_factory()
    create_investment_deposit(admin_client, application, 17)
    application.refresh_from_db()
    assert application.deposit is not None


@pytest.mark.django_db
def test_investment_application_refund(admin_client, asset_usd, cold_bank_account_factory, application_factory):
    cold_bank_account_factory(asset=asset_usd)
    application = application_factory()
    create_investment_deposit(admin_client, application, 17)
    application.refresh_from_db()
    assert application.deposit is not None

    model = InvestmentApplication
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
            'pk': application.pk,
            'tool': 'refund'
        })
    response = admin_client.get(url, {
        'confirm': 'yes'
    })
    assert response.status_code == 302
