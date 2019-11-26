import factory

from jibrel.authentication.factories import VerifiedUser
from jibrel.accounting.factories import AccountFactory

from .models import (
    BankAccount,
    CryptoAccount,
    DepositBankAccount,
    DepositCryptoAccount
)


class BankAccountFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(VerifiedUser)
    account = factory.SubFactory(AccountFactory)

    swift_code = "ADCBAEAATRY"
    bank_name = "ABU DHABI COMMERCIAL BANK"
    holder_name = factory.Faker('name')
    iban_number = factory.Faker('bban')

    class Meta:
        model = BankAccount


class DepositBankAccountFactory(factory.DjangoModelFactory):
    is_active = True
    account = factory.SubFactory(AccountFactory)
    bank_account_details = "This is a FAKE bank account details"

    class Meta:
        model = DepositBankAccount


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
