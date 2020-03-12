from django.db import (
    models,
    transaction
)

from django_banking.models import (
    Account,
    Asset
)
from django_banking.models.accounts.enum import AccountType
from django_banking.user import User


class FoloosiAccountManager(models.Manager):
    @transaction.atomic()
    def get_or_create(self, asset, **kwargs):
        """
        To avoid single account for wire transfer and card payments
        """
        account = self._create_payment_service_account(asset)

        kwargs['defaults'] = dict(kwargs.get('defaults', {}),
                                  account=account)

        obj, created = super().get_or_create(**kwargs)
        if not created:
            account.delete()

        return obj, created

    def create(self, user: User, customer_id: str, asset: Asset):
        account = self._create_payment_service_account(asset)
        return super().create(
            user=user,
            customer_id=customer_id,
            account=account
        )

    def _create_payment_service_account(self, asset):
        return Account.objects.create(
            asset=asset, type=AccountType.TYPE_NORMAL, strict=True
        )


class FoloosiChargeManager(models.Manager):
    @transaction.atomic()
    def create(self, user, operation, payment, **kwargs):
        from .models import UserFoloosiAccount
        foloosi_account = UserFoloosiAccount.objects.get_or_create(
            user=user,
            asset=operation.asset
        )
        operation.references['card_account'] = {
            'type': 'foloosi',
            'uuid': str(foloosi_account.pk)
        }
        operation.save(update_fields=['references'])
        return super().create(
            operation=operation,
            reference_token=payment["reference_token"]
        )
