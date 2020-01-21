import pytest

from django_banking.models import Asset
from django_banking.models.accounts.enum import AccountType
from tests.test_banking.factories.dajngo_banking import AccountFactory


@pytest.fixture()
def asset_factory(db):
    counter = 0

    def _asset_factory():
        nonlocal counter
        counter += 1
        return Asset.objects.create(name=f'Tmp{counter}', symbol=f'XY{counter}')

    return _asset_factory


@pytest.fixture()
def account_factory(db, asset_factory):
    def _account_factory(asset=None):
        asset = asset or asset_factory()
        return AccountFactory(type=AccountType.TYPE_ACTIVE, strict=True, asset=asset)

    return _account_factory
