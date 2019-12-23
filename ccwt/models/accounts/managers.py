from typing import List, Dict, Any

from django.db import models
from django.utils.functional import cached_property

from ccwt.models import Asset
from ccwt.models.accounts.enum import AccountType
from ccwt.user import User
from ccwt import logger


def user_account_queryset(user, assets=None):
    from .models import Account
    qs = Account.objects.filter(useraccount__user=user)
    if assets:
        qs = qs.filter(asset__in=assets)
    return qs.with_balances()


class UserAccountManager(models.Manager):

    """User account model manager.
    """

    def get_user_accounts(self,
                          user: User,
                          only_allowed_assets: bool = True) -> List['Account']:
        """Get all created user bookkeeping accounts.

        :param user: user instance
        :param only_allowed_assets: only accounts for allowed assets returned by default
        :return: list of user accounts
        """
        allowed_assets = Asset.objects.for_customer(user)

        user_accounts = user_account_queryset(
            user,
            allowed_assets if only_allowed_assets else None
        )

        clear = True

        # create missed accounts
        found_assets = {uac.asset for uac in user_accounts}
        for asset in allowed_assets:
            if asset not in found_assets:
                self.for_customer(user, asset)
                clear = False

        if clear:
            return user_accounts
        else:
            # query db again if new accounts created
            return user_account_queryset(
                user,
                allowed_assets if only_allowed_assets else None
            )

    def for_customer(self, user: User, asset: Asset) -> 'Account':
        """Get user' bookkeeping account for specified asset.

        New account will be created if user account for specified asset
        didn't found.
        """
        from .models import Account
        try:
            obj = self.get(user=user, account__asset=asset).account
            logger.debug("UserAccount account %s used as UserAccount "
                         "for user %s and asset %s",
                         obj, user, asset)
            return obj
        except self.model.DoesNotExist:
            acc = Account.objects.create(
                asset=asset,
                type=AccountType.TYPE_ACTIVE,
                strict=False
            )
            self.create(user=user, account=acc)
            logger.info(
                "UserAccount account %s for currency %s, user %s created",
                acc, asset, user
            )
            return acc



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
        from .models import Account
        return Account.objects.filter(**{
            f'{self._related_name_from_account}__user': user,
            'asset__in': assets,
        }).with_balances()

    def get_user_accounts(self, user: User, assets: List[Asset] = None) -> List['Account']:
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

    def for_customer(self, user: User, asset: Asset) -> 'Account':
        """Get user' bookkeeping account for specified asset.

        New account will be created if user account for specified asset
        didn't found.
        """
        from .models import Account
        try:
            return self.get(user=user, account__asset=asset).account
        except self.model.DoesNotExist:
            acc = Account.objects.create(
                asset=asset,
                **self._account_creation_kwargs
            )
            self.create(user=user, account=acc)
            return acc


