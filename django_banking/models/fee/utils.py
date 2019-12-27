import functools
from decimal import (
    ROUND_DOWN,
    Decimal
)

from django_banking.core.data import Amount
from django_banking.models import (
    Asset,
    Fee
)
from django_banking.models.fee.enum import FeeOperationType


def calculate_fee(
    amount: Decimal,
    asset: Asset,
    operation_type: str,
) -> Amount:
    try:
        fee = Fee.objects.get(operation_type=operation_type, asset=asset)
    except Fee.DoesNotExist:
        fee = Fee.objects.get(operation_type=operation_type, asset__isnull=True)
    fee_amount = fee.calculate(amount)
    return Amount.quantize(fee_amount, decimals=asset.decimals, rounding=ROUND_DOWN)


calculate_fee_crypto_withdrawal = functools.partial(
    calculate_fee, operation_type=FeeOperationType.WITHDRAWAL_CRYPTO
)
calculate_fee_bank_account_withdrawal = functools.partial(
    calculate_fee, operation_type=FeeOperationType.WITHDRAWAL_BANK_ACCOUNT
)
calculate_fee_card_deposit = functools.partial(
    calculate_fee, operation_type=FeeOperationType.DEPOSIT_CARD
)
