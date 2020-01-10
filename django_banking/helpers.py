from pprint import pformat
from textwrap import indent

from django_banking import logger


def render_relations(account):
    result = []

    relations = {
        'UserAccount': 'useraccount_set',
        'BankAccount': 'bankaccount_set',
        'DepositBankAccount': 'depositbankaccount_set',
        'CryptoAccount': 'cryptoaccount_set',
        'DepositCryptoAccount': 'depositcryptoaccount_set',
        'FeeUserAccount': 'feeuseraccount_set',
        'ExchangeUserAccount': 'exchangeuseraccount_set',
        'RoundingUserAccount': 'roundinguseraccount_set',
        'CardAccount': 'cardaccount_set',
    }

    for label, related_name in relations.items():
        if not hasattr(account, related_name):
            logger.warning("No relation %s found on prettified "
                           "operation account %s",
                           related_name, account)
            continue
        qs = getattr(account, related_name).all()
        for obj in qs:
            result.append(
                f"* {label} {getattr(obj, 'user', '')} ({obj.uuid})\n"
            )

    return ''.join(result)


def render_account_info(account):
    relations = render_relations(account)
    references = indent(pformat(account.references), prefix='\t').lstrip('\t')
    return (
        f"{relations}"
        f"Type: {account.get_type_display()}\n"
        f"Balance: {account.calculate_balance()}\n"
        f"Account references: {references}"
    )


class pretty_operation:
    def __init__(self, operation):
        self.operation = operation

    @classmethod
    def render_tx(cls, tx):
        account_info = indent(render_account_info(tx.account), prefix='\t')
        references = indent(pformat(tx.references), prefix='\t').lstrip('\t')
        return (
            f"\n"
            f"TX {tx.uuid}\n"
            f"Amount: {tx.amount} {tx.account.asset.symbol}\n"
            f"Account: {tx.account.uuid}\n"
            f"{account_info}\n"
            f"TX references: {references}"
            f"\n"
        )

    def __str__(self):
        transactions = [
            self.render_tx(tx) for tx in self.operation.transactions.all()
        ]
        references = pformat(self.operation.references)
        return (
            f"\n[Operation] {self.operation.uuid}\n\n"
            f"Status: {self.operation.get_status_display()}\n"
            f"References: {references}\n"
            f"Metadata: {references}\n"
            f"{''.join(transactions)}\n"
        )


class pretty_account:
    def __init__(self, account):
        self.account = account

    def __str__(self):
        return render_account_info(self.account)
