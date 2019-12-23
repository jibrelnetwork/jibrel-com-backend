from factory import (
    DjangoModelFactory,
    Faker,
    Sequence,
    SubFactory,
    post_generation
)

from jibrel.assets import (
    AssetPair,
    AssetPairFactory
)

from jibrel.accounting.models import (
    Account,
    Asset,
    Operation,
    Transaction
)


class AssetFactory(DjangoModelFactory):
    name = Faker('company')
    symbol = Sequence(lambda n: f'SYM{n}')
    country = 'AR'
    type = 'crypto'

    class Meta:
        model = Asset

    @post_generation
    def asset_pairs(self, create, extracted, **kwargs):
        if self.type == Asset.CRYPTO:
            fiats = Asset.objects.filter(type=Asset.FIAT)
            for fiat in fiats:
                if AssetPair.objects.filter(base=self, quote=fiat).exists():
                    continue
                AssetPairFactory.create(base=self, quote=fiat)
        elif self.type == Asset.FIAT:
            cryptos = Asset.objects.filter(type=Asset.CRYPTO)
            for crypto in cryptos:
                if AssetPair.objects.filter(base=crypto, quote=self).exists():
                    continue
                AssetPairFactory.create(base=crypto, quote=self)


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction


class AccountFactory(DjangoModelFactory):
    type = Account.TYPE_NORMAL
    strict = False

    asset = SubFactory(AssetFactory)

    class Meta:
        model = Account


class DepositOperationFactory(DjangoModelFactory):
    class Meta:
        model = Operation

    type = Operation.DEPOSIT

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
