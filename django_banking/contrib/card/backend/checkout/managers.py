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
from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class CheckoutAccountManager(models.Manager):
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


class CheckoutChargeManager(models.Manager):
    @transaction.atomic()
    def create(self, user, operation, token, **kwargs):
        from django_banking.contrib.card.backend.checkout.models import UserCheckoutAccount
        checkout_account = None
        try:
            checkout_account = UserCheckoutAccount.objects.get(
                user=user
            )
            customer = {
                'customer_id': checkout_account.customer_id
            }
        except ObjectDoesNotExist:
            kyc = user.profile.last_kyc.details
            customer = {
                'email': kyc.email,
                'name': f'{kyc.first_name} {kyc.last_name}'
            }

        api = CheckoutAPI()
        amount = operation.amount
        payment = api.create(customer, amount, token)
        if not checkout_account:
            checkout_account = UserCheckoutAccount.objects.get(
                user=user,
                customer_id=payment.customer.id
            )
        # TODO check operation
        return super().create(
            payment.id,
            **kwargs
        )
        charge_id



