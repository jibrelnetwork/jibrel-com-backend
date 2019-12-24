import factory

from ccwt.contrib.crypto.models import CryptoAccount, DepositCryptoAccount
from ccwt.tests.factories import AccountFactory


class CryptoAccountFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(AccountFactory)
    address = '0x12345677'

    class Meta:
        model = CryptoAccount


class DepositCryptoAccountFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(AccountFactory)
    address = factory.Sequence(lambda n: f'0x1234567{n}')

    class Meta:
        model = DepositCryptoAccount
