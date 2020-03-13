from django.core.exceptions import ObjectDoesNotExist
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


class CheckoutAccountManager(models.Manager):
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


class CheckoutChargeManager(models.Manager):
    @transaction.atomic()
    def create(self, user, operation, payment, **kwargs):
        from .models import UserCheckoutAccount
        asset = operation.asset
        try:
            user.checkout_account
        except ObjectDoesNotExist:
            UserCheckoutAccount.objects.create(
                user=user,
                customer_id=payment.customer.id,
                asset=asset
            )
        return super().create(
            operation=operation,
            charge_id=payment.id,
            payment_status=payment.status.lower(),
            redirect_link=payment.redirect_link.href if payment.is_pending and payment.requires_redirect else None,
            **kwargs
        )
