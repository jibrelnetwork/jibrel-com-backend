import factory

from django_banking.contrib.crypto.models import (
    UserCryptoAccount,
    UserCryptoDepositAccount
)
from django_banking.tests.factories import AccountFactory


class CryptoAccountFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(AccountFactory)
    address = '0x12345677'

    class Meta:
        model = UserCryptoAccount


class DepositCryptoAccountFactory(factory.DjangoModelFactory):
    account = factory.SubFactory(AccountFactory)
    address = factory.Sequence(lambda n: f'0x1234567{n}')

    class Meta:
        model = UserCryptoDepositAccount
