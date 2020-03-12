from uuid import uuid4

from django.db import models

from django_banking import module_name
from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus
from django_banking.contrib.card.backend.checkout.managers import (
    CheckoutAccountManager,
    CheckoutChargeManager
)
from django_banking.models import (
    Account,
    Operation
)
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

    charge_id = models.CharField(max_length=30, db_index=True)
    payment_status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    redirect_link = models.URLField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CheckoutChargeManager()

    def update_deposit_status(self):
        if self.payment_status in (
            CheckoutStatus.VOIDED,
            CheckoutStatus.REFUNDED,
            CheckoutStatus.VERIFIED,
            CheckoutStatus.PARTIALLY_CAPTURED,
            CheckoutStatus.PARTIALLY_REFUNDED,
            CheckoutStatus.PAID,
            CheckoutStatus.DECLINED
        ):
            self.operation.reject('Processing error')

        elif self.payment_status == CheckoutStatus.PENDING:
            self.operation.action_required()

        elif self.payment_status == CheckoutStatus.AUTHORIZED:
            self.operation.hold()

        elif self.payment_status == CheckoutStatus.CAPTURED:
            self.operation.hold(commit=False)
            self.operation.commit()

        elif self.payment_status == CheckoutStatus.CANCELLED:
            self.operation.cancel()

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
    def requires_redirect(self):
        return bool(self.redirect_link)

    class Meta:
        db_table = f'{module_name}_checkoutcharge'
        ordering = ['-created_at']
