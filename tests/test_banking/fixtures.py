import pytest

from django_banking.contrib.wire_transfer.models import ColdBankAccount
from django_banking.models import Asset
from django_banking.models.accounts.enum import AccountType
from django_banking.models.assets.enum import AssetType
from tests.test_banking.factories.dajngo_banking import AccountFactory
from tests.test_banking.factories.wire_transfer import ColdBankAccountFactory


@pytest.fixture()
def asset_factory(db):
    def _asset_factory():
        counter = Asset.objects.count() + 1
        return Asset.objects.create(name=f'Tmp{counter}', symbol=f'XY{counter}')

    return _asset_factory


@pytest.fixture()
def asset_usd(db):
    return Asset.objects.get(type=AssetType.FIAT)


@pytest.fixture()
def account_factory(db, asset_factory):
    def _account_factory(asset=None):
        asset = asset or asset_factory()
        return AccountFactory(type=AccountType.TYPE_ACTIVE, strict=True, asset=asset)

    return _account_factory


@pytest.fixture()
def cold_bank_account_factory(db, asset_usd):
    def _cold_bank_account_factory(asset=None):
        asset = asset or asset_usd
        try:
            return ColdBankAccount.objects.get(account__asset=asset)
        except ColdBankAccount.DoesNotExist:
            return ColdBankAccountFactory(account__asset=asset)

    return _cold_bank_account_factory
