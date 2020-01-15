from decimal import (
    ROUND_HALF_UP,
    Decimal
)
from typing import Union


def rounded(value: Union[int, Decimal, float], decimal_places: int = 2) -> Decimal:
    value = value if isinstance(value, Decimal) else Decimal(value)
    return Decimal(value.quantize(Decimal(str(10 ** -decimal_places)), rounding=ROUND_HALF_UP))
