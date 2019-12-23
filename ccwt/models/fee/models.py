from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint

from ccwt.models import Asset
from .enum import FeeOperationType, FeeValueType


class Fee(models.Model):
    VALUE_TYPE_CHOICES = (
        (FeeValueType.CONSTANT, 'Constant'),
        (FeeValueType.PERCENTAGE, 'Percentage'),
    )

    OPERATION_TYPE_CHOICES = (
        (FeeOperationType.WITHDRAWAL_CRYPTO, 'Withdrawal crypto'),
        (FeeOperationType.WITHDRAWAL_BANK_ACCOUNT, 'Withdrawal bank account'),
        (FeeOperationType.DEPOSIT_CRYPTO, 'Deposit crypto'),
        (FeeOperationType.DEPOSIT_BANK_ACCOUNT, 'Deposit bank account'),
        (FeeOperationType.DEPOSIT_CARD, 'Deposit card'),
    )
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation_type = models.CharField(max_length=30, choices=OPERATION_TYPE_CHOICES)
    asset = models.ForeignKey(Asset, null=True, on_delete=models.CASCADE)
    value_type = models.CharField(max_length=30, choices=VALUE_TYPE_CHOICES)
    value = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=settings.ACCOUNTING_DECIMAL_PLACES
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['asset', 'operation_type'], name='unique_asset_and_operation_type',
            )
        ]

    def calculate(self, amount: Decimal) -> Decimal:
        if self.value_type == FeeValueType.CONSTANT:
            return self.value
        elif self.value_type == FeeValueType.PERCENTAGE:
            return self.value * amount
        raise ValueError('You must specify value_type')
