import logging
from decimal import Decimal
from typing import Dict

from django.db import (
    models,
    transaction
)

from django_banking.models import (
    Asset,
    Operation,
    UserAccount
)
from django_banking.models.transactions.queryset import OperationQuerySet
from django_banking.user import User

logger = logging.getLogger(__name__)


class CryptoAccountManager(models.Manager):
    pass


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


class DepositCryptoOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_crypto()

    def create_deposit(self, deposit_crypto_account, amount: Decimal, metadata: Dict = None):
        from .models import UserCryptoDepositAccount
        assert isinstance(deposit_crypto_account, UserCryptoDepositAccount)
        user = deposit_crypto_account.user
        asset = deposit_crypto_account.account.asset
        # TODO
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


class WithdrawalCryptoOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_crypto()
