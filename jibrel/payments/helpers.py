import decimal
import logging
from typing import Any, Dict, List

from dataclasses import dataclass
from pprint import pformat
from textwrap import indent

from django.db import models
from django.utils.functional import cached_property

from jibrel.authentication.models import User
from jibrel.accounting.models import Account, Asset


logger = logging.getLogger(__name__)


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


@dataclass
class Amount:
    rounded: decimal.Decimal
    remainder: decimal.Decimal
    decimals: int
    rounding: str  # decimal.ROUND_UP, decimal.ROUND_DOWN, etc.

    @classmethod
    def quantize(cls, amount: decimal.Decimal, decimals: int, rounding: str) -> 'Amount':
        rounded = amount.quantize(
            decimal.Decimal('.1') ** decimals,
            rounding=rounding
        )
        return cls(
            rounded=rounded,
            remainder=amount - rounded,
            decimals=decimals,
            rounding=rounding,
        )






class BaseUserAccountManager(models.Manager):
    """Base user account model manager.
    """

    def __init__(self, account_creation_kwargs: Dict[str, Any] = None):
        super(BaseUserAccountManager, self).__init__()
        if account_creation_kwargs is None:
            account_creation_kwargs = {}
        self._account_creation_kwargs = account_creation_kwargs

    @cached_property
    def _related_name_from_account(self):
        return self.model._meta.get_field('account').related_query_name()

    def _get_user_account_queryset(self, user, assets):
        return Account.objects.filter(**{
            f'{self._related_name_from_account}__user': user,
            'asset__in': assets,
        }).with_balances()

    def get_user_accounts(self, user: User, assets: List[Asset] = None) -> List[Account]:
        """Get all created user bookkeeping accounts.

        :param user: user instance
        :return: list of user accounts
        """
        available_assets = assets
        if available_assets is None:
            available_assets = Asset.objects.for_customer(user)

        user_accounts = self._get_user_account_queryset(user, available_assets)

        clear = True

        # create missed accounts
        found_assets = {uac.asset for uac in user_accounts}
        for asset in available_assets:
            if asset not in found_assets:
                self.for_customer(user, asset)
                clear = False

        if clear:
            return user_accounts
        else:
            # query db again if new accounts created
            return self._get_user_account_queryset(user, available_assets)

    def for_customer(self, user: User, asset: Asset) -> Account:
        """Get user' bookkeeping account for specified asset.

        New account will be created if user account for specified asset
        didn't found.
        """
        try:
            return self.get(user=user, account__asset=asset).account
        except self.model.DoesNotExist:
            acc = Account.objects.create(
                asset=asset,
                **self._account_creation_kwargs
            )
            self.create(user=user, account=acc)
            return acc
