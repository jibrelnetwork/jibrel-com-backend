from decimal import (
    Decimal,
    InvalidOperation
)

def sanitize_amount(value, decimal_places=None):
    try:
        amount = Decimal(value)

        if decimal_places:
            decimal_exp = Decimal('10') ** -decimal_places
            if amount.quantize(decimal_exp) != amount:
                raise InvalidException(target='amount',
                                       message='Value precision error')
    except (InvalidOperation, TypeError):
        raise InvalidException(target='amount',
                               message='Invalid amount value')

    if amount <= 0:
        raise InvalidException(target='amount',
                               message='Amount must be greater than 0')

    return amount
