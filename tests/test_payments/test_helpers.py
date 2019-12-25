import pytest

from django_banking.contrib.wire_transfer.models import UserBankAccount
from django_banking.helpers import pretty_operation
from django_banking.models import UserAccount, Operation
from jibrel.authentication.factories import VerifiedUser
from tests.test_banking.factories.wire_transfer import BankAccountFactory


@pytest.mark.django_db
def test_pretty_operation():
    user = VerifiedUser.create()
    bank_account: UserBankAccount = BankAccountFactory.create(user=user)
    user_account = UserAccount.objects.for_customer(
        user, bank_account.account.asset
    )
    op = Operation.objects.create_deposit(
        payment_method_account=bank_account.account,
        user_account=user_account,
        amount=10
    )
    op.hold()
    op.commit()

    print(pretty_operation(op))
