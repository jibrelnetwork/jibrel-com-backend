from decimal import (
    ROUND_HALF_UP,
    Decimal
)
from typing import Union


def rounded(value: Union[int, Decimal, float], decimal_places: int = 2) -> Decimal:
    value = value if isinstance(value, Decimal) else Decimal(value)
    return Decimal(value.quantize(Decimal(f'.{"0" * (decimal_places-1)}1'), rounding=ROUND_HALF_UP))
