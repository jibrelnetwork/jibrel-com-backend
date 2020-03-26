from uuid import uuid4

from django.db import models

from django_banking import module_name
from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus
from django_banking.contrib.card.backend.foloosi.managers import (
    FoloosiAccountManager,
    FoloosiChargeManager
)
from django_banking.models import (
    Account,
    Operation
)
from django_banking.settings import USER_MODEL


class UserFoloosiAccount(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.OneToOneField(to=USER_MODEL, on_delete=models.PROTECT, related_name='foloosi_account')

    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    objects = FoloosiAccountManager()

    class Meta:
        db_table = f'{module_name}_foloosiaccount'


class FoloosiCharge(models.Model):
    STATUS_CHOICES = (
        (FoloosiStatus.PENDING, 'pending'),
        (FoloosiStatus.CAPTURED, 'success'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation = models.ForeignKey(
        Operation, on_delete=models.PROTECT, null=True,
        related_name='charge_foloosi'
    )

    charge_id = models.CharField(max_length=30, null=True, db_index=True)
    payment_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=FoloosiStatus.PENDING)
    reference_token = models.CharField(max_length=512)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FoloosiChargeManager()

    def update_deposit_status(self):
        if self.payment_status == FoloosiStatus.REFUND_MANUALLY:
            Operation.objects.create_refund(
                deposit=self.operation,
                amount=self.operation.amount
            )
            self.operation.save(update_fields=('updated_at',))

        if self.payment_status == FoloosiStatus.PENDING:
            self.operation.action_required()

        elif self.payment_status == FoloosiStatus.CAPTURED:
            self.operation.hold(commit=False)
            self.operation.commit()

        else:
            self.operation.save(update_fields=('updated_at',))

    def update_status(self, status):
        self.payment_status = status.lower()
        self.save(update_fields=['payment_status', 'updated_at', 'charge_id'])
        self.update_deposit_status()

    @property
    def is_success(self):
        return self.payment_status == FoloosiStatus.CAPTURED

    class Meta:
        db_table = f'{module_name}_foloosicharge'
        ordering = ['-created_at']
