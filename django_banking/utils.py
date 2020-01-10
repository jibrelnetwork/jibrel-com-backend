import random
from decimal import Decimal

from django_banking.limitations.data import Limit
from django_banking.limitations.enum import (
    LimitInterval,
    LimitType
)


def generate_deposit_reference_code():
    alphabet = list(range(0, 9))
    code_length = 9
    code = ''.join([
        str(random.choice(alphabet)) for x in range(code_length)
    ])
    return "DEPOSIT-{}-{}-{}".format(code[:3], code[3:6], code[6:])


def get_limit(asset_symbol: str, value: Decimal, limit_type: str, interval: str = None):
    kw = {
        'interval': getattr(LimitInterval, interval)
    } if interval else {}

    return Limit(
        asset_symbol=asset_symbol,
        value=value,
        type=getattr(LimitType, limit_type),
        **kw
    )


def limit_parser(limits):
    if isinstance(limits, (list, tuple)):
        return [get_limit(**lim) for lim in limits]
    elif isinstance(limits, dict):
        return {k: limit_parser(lim) for k, lim in limits.items()}
