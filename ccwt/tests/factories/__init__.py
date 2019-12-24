from factory import (
    DjangoModelFactory,
    Faker,
    Sequence,
    SubFactory,
    post_generation
)

from ccwt.models import Asset, Operation, Account, Transaction
from ccwt.models.accounts.enum import AccountType
from ccwt.models.transactions.enum import OperationType


class AssetFactory(DjangoModelFactory):
    name = Faker('company')
    symbol = Sequence(lambda n: f'SYM{n}')
    country = 'AR'
    type = 'crypto'

    class Meta:
        model = Asset


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction


class AccountFactory(DjangoModelFactory):
    type = AccountType.TYPE_NORMAL
    strict = False

    asset = SubFactory(AssetFactory)

    class Meta:
        model = Account


class DepositOperationFactory(DjangoModelFactory):
    class Meta:
        model = Operation

    type = OperationType.DEPOSIT

    @post_generation
    def transactions(self, create, extracted, **kwargs):
        """Transactions post-generation hook.

        TODO: allow to pass [(account, amount)] structure to factory to allow
            transactions customization.
        """
        asset = AssetFactory.create()
        self.user_account = AccountFactory.create(asset=asset)
        right = AccountFactory.create(asset=asset)
        TransactionFactory.create(operation=self, account=self.user_account, amount=10)
        TransactionFactory.create(operation=self, account=right, amount=-10)
