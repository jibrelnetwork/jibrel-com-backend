from django.db import (
    models,
    transaction
)

from django_banking.models import (
    Account,
    Asset
)
from django_banking.user import User


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





class DepositCardOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).deposit_card()


class WithdrawalCardOperationManager(models.Manager):
    def get_queryset(self):
        return OperationQuerySet(model=self.model, using=self._db, hints=self._hints).withdrawal_card()
