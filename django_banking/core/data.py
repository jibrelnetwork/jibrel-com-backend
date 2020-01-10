import decimal
from dataclasses import dataclass


@dataclass
class Amount:
    rounded: decimal.Decimal
    remainder: decimal.Decimal
    decimals: int
    rounding: str  # decimal.ROUND_UP, decimal.ROUND_DOWN, etc.

    @classmethod
    def quantize(cls, amount: decimal.Decimal, decimals: int, rounding: str) -> 'Amount':
        rounded = amount.quantize(
            decimal.Decimal('.1') ** decimals,
            rounding=rounding
        )
        return cls(
            rounded=rounded,
            remainder=amount - rounded,
            decimals=decimals,
            rounding=rounding,
        )
