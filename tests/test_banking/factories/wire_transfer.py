import factory

from django_banking.contrib.wire_transfer.models import DepositBankAccount, BankAccount
from django_banking.tests.factories import AccountFactory
from jibrel.authentication.factories import VerifiedUser


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
