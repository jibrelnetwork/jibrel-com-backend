import pytest

from jibrel.authentication.factories import VerifiedUser
from jibrel.payments.factories import BankAccountFactory
from jibrel.payments.models import BankAccount, UserAccount
from jibrel.accounting.models import Operation
from jibrel.payments.helpers import pretty_operation


@pytest.mark.django_db
def test_pretty_operation():
    user = VerifiedUser.create()
    bank_account: BankAccount = BankAccountFactory.create(user=user)
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
