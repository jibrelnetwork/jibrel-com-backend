import factory

from django_banking.contrib.wire_transfer.models import (
    ColdBankAccount,
    UserBankAccount
)
from jibrel.authentication.factories import VerifiedUser

from .dajngo_banking import AccountFactory


class BankAccountFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(VerifiedUser)
    account = factory.SubFactory(AccountFactory)

    swift_code = "ADCBAEAATRY"
    bank_name = "ABU DHABI COMMERCIAL BANK"
    holder_name = factory.Faker('name')
    iban_number = factory.Faker('bban')

    class Meta:
        model = UserBankAccount


class ColdBankAccountFactory(factory.DjangoModelFactory):
    is_active = True
    account = factory.SubFactory(AccountFactory)
    holder_name = 'HOLDER'
    iban_number = 'TEST'
    account_number = 'TEST'
    bank_name = 'TEST'
    branch_address = 'BRANCH'
    swift_code = 'TEST'

    class Meta:
        model = ColdBankAccount
