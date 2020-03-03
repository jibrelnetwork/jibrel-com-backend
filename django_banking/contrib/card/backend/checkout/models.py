from uuid import uuid4

from django.db import models
from django.utils import timezone

from django_banking import module_name
from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus, ChargeStatus
from django_banking.contrib.card.backend.checkout.managers import CheckoutAccountManager
from django_banking.models import Operation
from django_banking.settings import USER_MODEL
from django_banking.models import Account
from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class UserCheckoutAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(to=USER_MODEL, on_delete=models.PROTECT)

    customer_id = models.CharField(max_length=30, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    objects = CheckoutAccountManager()

    class Meta:
        db_table = f'{module_name}_checkoutaccount'


class CheckoutCharge(models.Model):
    STATUS_CHOICES = (
        (CheckoutStatus.AUTHORIZED, 'authorized'),
        (CheckoutStatus.PENDING, 'pending'),
        (CheckoutStatus.VERIFIED, 'verified'),
        (CheckoutStatus.CAPTURED, 'captured'),
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
    redirect_link = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def status(self):
        if not self.charge_id:
            return ChargeStatus.SUCCESS
        return {
            CheckoutStatus.AUTHORIZED: ChargeStatus.PENDING,
            CheckoutStatus.PENDING: ChargeStatus.VALIDATING,
            CheckoutStatus.VERIFIED: ChargeStatus.PENDING,
            CheckoutStatus.CAPTURED: ChargeStatus.SUCCESS,
            CheckoutStatus.DECLINED: ChargeStatus.ERROR,
            CheckoutStatus.PAID: ChargeStatus.SUCCESS,
        }

    @property
    def is_success(self):
        return self.status == ChargeStatus.SUCCESS

    @property
    def is_error(self):
        return self.status == ChargeStatus.ERROR

    @property
    def is_processed(self):
        return self.is_success or self.is_error

    def status_latest(self, force=False):
        now = timezone.now()
        if not self.is_processed and (force or (now - self.updated_at).seconds < 15):
            self.payment_status = CheckoutAPI().get(self.charge_id).status
            self.updated_at = now
            self.save()
        return self.status

    @property
    def requires_redirect(self):
        return bool(self.redirect_link)
