import functools
from decimal import (
    ROUND_DOWN,
    Decimal
)

from ccwt.core.data import Amount
from ccwt.models import Asset, Fee
from ccwt.models.fee.enum import FeeOperationType


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
    calculate_fee, operation_type=FeeOperationType.OPERATION_TYPE_WITHDRAWAL_CRYPTO
)
calculate_fee_bank_account_withdrawal = functools.partial(
    calculate_fee, operation_type=FeeOperationType.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT
)
calculate_fee_card_deposit = functools.partial(
    calculate_fee, operation_type=FeeOperationType.OPERATION_TYPE_DEPOSIT_CARD
)
