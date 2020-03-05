from uuid import uuid4

from django.db import models
from django.utils import timezone

from django_banking import module_name
from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI
from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus
from django_banking.contrib.card.backend.checkout.managers import (
    CheckoutAccountManager,
    CheckoutChargeManager
)
from django_banking.models import (
    Account,
    Operation
)
from django_banking.models.transactions.enum import OperationStatus
from django_banking.settings import USER_MODEL


class UserCheckoutAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.OneToOneField(to=USER_MODEL, on_delete=models.PROTECT, related_name='checkout_account')

    customer_id = models.CharField(max_length=30, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    objects = CheckoutAccountManager()

    class Meta:
        db_table = f'{module_name}_checkoutaccount'


class CheckoutCharge(models.Model):
    STATUS_CHOICES = (
        (CheckoutStatus.PENDING, 'pending'),
        (CheckoutStatus.AUTHORIZED, 'authorized'),
        (CheckoutStatus.VERIFIED, 'card verified'),
        (CheckoutStatus.VOIDED, 'voided'),
        (CheckoutStatus.PARTIALLY_CAPTURED, 'partially captured'),
        (CheckoutStatus.CAPTURED, 'captured'),
        (CheckoutStatus.PARTIALLY_REFUNDED, 'partially refunded'),
        (CheckoutStatus.REFUNDED, 'refunded'),
        (CheckoutStatus.CANCELLED, 'cancelled'),
        (CheckoutStatus.DECLINED, 'declined'),
        (CheckoutStatus.PAID, 'paid'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation = models.ForeignKey(
        Operation, on_delete=models.PROTECT, null=True,
        related_name='charge_checkout'
    )

    charge_id = models.CharField(max_length=30, null=True, db_index=True)
    payment_status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    redirect_link = models.URLField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CheckoutChargeManager()

    @staticmethod
    def get_deposit_status(payment_status):
        return {
            CheckoutStatus.PENDING: OperationStatus.THREEDS,
            CheckoutStatus.AUTHORIZED: OperationStatus.HOLD,
            # CheckoutStatus.VERIFIED: OperationStatus.HOLD,  # its not
            CheckoutStatus.CAPTURED: OperationStatus.HOLD,
            # CheckoutStatus.REFUNDED: OperationStatus.COMMITTED,  # TODO
            CheckoutStatus.CANCELLED: OperationStatus.CANCELLED,
            CheckoutStatus.DECLINED: OperationStatus.ERROR,
            CheckoutStatus.PAID: OperationStatus.COMMITTED,
        }[payment_status]

    def update_deposit_status(self):
        self.operation.status = self.get_deposit_status(self.payment_status)
        self.operation.save(update_fields=['status'])

    def update_status(self, status):
        self.payment_status = status.lower()
        self.save(update_fields=['payment_status'])
        self.update_deposit_status()

    @property
    def is_success(self):
        return self.payment_status in (
            CheckoutStatus.CAPTURED,
            CheckoutStatus.PAID,
        )

    @property
    def is_error(self):
        return self.payment_status == CheckoutStatus.DECLINED

    @property
    def is_processed(self):
        return self.is_success or self.is_error

    @property
    def latest_status(self):
        now = timezone.now()
        if not self.is_processed and (now - self.updated_at).seconds < 15:
            self.payment_status = CheckoutAPI().get(self.charge_id).status
            self.updated_at = now
            self.save()
        return self.payment_status

    @property
    def requires_redirect(self):
        return bool(self.redirect_link)

    class Meta:
        db_table = f'{module_name}_checkoutcharge'
