import functools
from decimal import (
    ROUND_DOWN,
    Decimal
)

from jibrel.accounting import Asset
from jibrel.payments.helpers import Amount
from jibrel.payments.models import Fee


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
    calculate_fee, operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_CRYPTO
)
calculate_fee_bank_account_withdrawal = functools.partial(
    calculate_fee, operation_type=Fee.OPERATION_TYPE_WITHDRAWAL_BANK_ACCOUNT
)
calculate_fee_card_deposit = functools.partial(
    calculate_fee, operation_type=Fee.OPERATION_TYPE_DEPOSIT_CARD
)
