from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from .enum import LimitType

from ccwt.limitations.enum import LimitType, LimitInterval
from ccwt.models.transactions.enum import OperationType

OPERATION_TYPE_MAP = {
    LimitType.DEPOSIT: OperationType.DEPOSIT,
    LimitType.WITHDRAWAL: OperationType.WITHDRAWAL
}


LIMIT_TYPE_MAP = {
    v: k for k, v in OPERATION_TYPE_MAP.items()
}


class Limit(NamedTuple):

    """Limit definition.
    """

    asset_symbol: str
    value: Decimal
    type: LimitType
    interval: LimitInterval = LimitInterval.WEEK


class UserLimit(NamedTuple):
    asset: str
    total: Decimal
    available: Decimal
    type: LimitType
    interval: LimitInterval
    reset_date: datetime

