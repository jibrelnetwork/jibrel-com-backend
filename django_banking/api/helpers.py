from decimal import (
    Decimal,
    InvalidOperation
)
from rest_framework import exceptions


def sanitize_amount(value, decimal_places=None):
    try:
        amount = Decimal(value)

        if decimal_places:
            decimal_exp = Decimal('10') ** -decimal_places
            if amount.quantize(decimal_exp) != amount:
                raise exceptions.ValidationError('Value precision error')
    except (InvalidOperation, TypeError):
        raise exceptions.ValidationError('Invalid amount value')

    if amount <= 0:
        raise exceptions.ValidationError('Amount must be greater than 0')

    return amount
