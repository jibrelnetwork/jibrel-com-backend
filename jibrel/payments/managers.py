import logging
from decimal import Decimal
from typing import Dict, List

from django.db import models, transaction

from jibrel.authentication.models import User
from jibrel.accounting.models import Account, Asset, Operation
from jibrel.assets.models import AssetPair
from jibrel.exchanges.repositories.price import price_repository

from .queryset import OperationQuerySet

logger = logging.getLogger(__name__)


def user_account_queryset(user, assets=None):
    qs = Account.objects.filter(useraccount__user=user)
    if assets:
        qs = qs.filter(asset__in=assets)
    return qs.with_balances()


class UserAccountManager(models.Manager):

    """User account model manager.
    """

    def get_user_accounts(self,
                          user: User,
                          only_allowed_assets: bool = True) -> List[Account]:
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

    def for_customer(self, user: User, asset: Asset) -> Account:
        """Get user' bookkeeping account for specified asset.

        New account will be created if user account for specified asset
        didn't found.
        """
        try:
            obj = self.get(user=user, account__asset=asset).account
            logger.debug("UserAccount account %s used as UserAccount "
                         "for user %s and asset %s",
                         obj, user, asset)
            return obj
        except self.model.DoesNotExist:
            acc = Account.objects.create(
                asset=asset,
                type=Account.TYPE_ACTIVE,
                strict=False
            )
            self.create(user=user, account=acc)
            logger.info(
                "UserAccount account %s for currency %s, user %s created",
                acc, asset, user
            )
            return acc


class BankAccountManager(models.Manager):
    def create(self, **kwargs):
        if 'account' not in kwargs:
            asset = Asset.objects.get(country=kwargs['user'].get_residency_country_code())
            kwargs['account'] = Account.objects.create(
                asset=asset, type=Account.TYPE_NORMAL, strict=False
            )
        return super().create(**kwargs)


class DepositCryptoAccountManager(models.Manager):
    def for_customer(self, user: User, asset: Asset):
        with transaction.atomic():
            try:
                deposit_account = self.get(user=user, account__asset=asset)
                logger.debug("Use already binded account %s for %s deposits.",
                             deposit_account, user)
            except self.model.DoesNotExist:
                deposit_account = self.filter(
                    user__isnull=True, account__asset=asset
                ).select_for_update().first()

                if deposit_account is None:
                    logger.error(
                        "%s asset has no active deposit crypto account. "
                        "Can't acquired account for %s",
                        asset, user
                    )
                    raise Exception(
                        "No address in crypto account withdrawal pool for asset "
                        "%s" % asset
                    )
                logger.info("Account %s binded to user %s", deposit_account, user)
                deposit_account.user = user
                deposit_account.save()
            return deposit_account


class CryptoAccountManager(models.Manager):
    pass


class CardAccountManager(models.Manager):
    def get_or_create(self, asset, **kwargs):
        with transaction.atomic():
            account = self._create_payment_service_account(asset)

            kwargs['defaults'] = dict(kwargs.get('defaults', {}),
                                      account=account)

            obj, created = super().get_or_create(**kwargs)
            if not created:
                account.delete()

        return obj, created

    def create(self, user: User, tap_card_id: str, asset: Asset):
        account = self._create_payment_service_account(asset)
        return super().create(user=user, tap_card_id=tap_card_id, account=account)

    def _create_payment_service_account(self, asset):
        return Account.objects.create(asset=asset,
                                      type=Account.TYPE_NORMAL,
                                      strict=True)


class DepositCryptoOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_crypto()

    def create_deposit(self, deposit_crypto_account, amount: Decimal, metadata: Dict = None):
        from .models import DepositCryptoAccount, UserAccount
        assert isinstance(deposit_crypto_account, DepositCryptoAccount)
        user = deposit_crypto_account.user
        asset = deposit_crypto_account.account.asset
        asset_pair = AssetPair.objects.get(
            base=asset,
            quote__country__iexact=user.get_residency_country_code(),
        )
        price = price_repository.get_by_pair_id(asset_pair.pk)
        account = UserAccount.objects.for_customer(user=user, asset=asset)
        operation = Operation.objects.create_deposit(
            payment_method_account=deposit_crypto_account.account,
            user_account=account,
            amount=amount,
            metadata={
                'total_price': {
                    'asset_pair_id': str(asset_pair.pk),
                    'base_asset_id': str(asset.pk),
                    'quote_asset_id': str(asset_pair.quote.pk),
                    'sell_price': str(price.sell),
                    'buy_price': str(price.buy),
                    'total': str(price.sell * amount)
                },
                **(metadata or {})
            }
        )
        operation.commit()
        return self.get_queryset().with_asset().with_fee().with_amount().with_total_amount().get(pk=operation.pk)


class DepositWireTransferOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_wire_transfer()


class WithdrawalWireTransferOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_wire_transfer()


class WithdrawalCryptoOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_crypto()


class DepositCardOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_card()


class WithdrawalCardOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_card()
