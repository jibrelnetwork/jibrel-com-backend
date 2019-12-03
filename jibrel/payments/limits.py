"""Payment limits.
"""
import decimal
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, NamedTuple

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.db.models import Value as V
from django.db.models.functions import Abs, Coalesce

from jibrel.accounting import Asset, Operation, Transaction
from jibrel.payments.models import UserAccount

logger = logging.getLogger(__name__)


class LimitType(Enum):

    """Available limit types.
    """

    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'


class LimitInterval(Enum):

    """Available limit intervals.
    """

    OPERATION = 'operation'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'


class Limit(NamedTuple):

    """Limit definition.
    """

    asset_symbol: str
    value: Decimal
    type: LimitType
    interval: LimitInterval = LimitInterval.WEEK


# https://jibrelnetwork.atlassian.net/wiki/spaces/CMENA/pages/991297656/CoinMENA+Key+Values
LIMITS = {
    None: [
        Limit(asset_symbol='AED', value=Decimal('50000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='SAR', value=Decimal('51000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='BHD', value=Decimal('5000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='KWD', value=Decimal('4000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='OMR', value=Decimal('5000'), type=LimitType.WITHDRAWAL),

        Limit(asset_symbol='AED', value=Decimal('50000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='SAR', value=Decimal('51000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='BHD', value=Decimal('5000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='KWD', value=Decimal('4000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='OMR', value=Decimal('5000'), type=LimitType.DEPOSIT),
    ],
    'tier1': [
        Limit(asset_symbol='AED', value=Decimal('75000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='SAR', value=Decimal('75000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='BHD', value=Decimal('7500'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='KWD', value=Decimal('6000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='OMR', value=Decimal('7500'), type=LimitType.WITHDRAWAL),

        Limit(asset_symbol='AED', value=Decimal('75000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='SAR', value=Decimal('75000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='BHD', value=Decimal('7500'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='KWD', value=Decimal('6000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='OMR', value=Decimal('7500'), type=LimitType.DEPOSIT),
    ],
    'tier2': [
        Limit(asset_symbol='AED', value=Decimal('100000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='SAR', value=Decimal('100000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='BHD', value=Decimal('10000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='KWD', value=Decimal('8000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='OMR', value=Decimal('10000'), type=LimitType.WITHDRAWAL),

        Limit(asset_symbol='AED', value=Decimal('100000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='SAR', value=Decimal('100000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='BHD', value=Decimal('10000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='KWD', value=Decimal('8000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='OMR', value=Decimal('10000'), type=LimitType.DEPOSIT),
    ],
    'tier3': [
        Limit(asset_symbol='AED', value=Decimal('250000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='SAR', value=Decimal('255000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='BHD', value=Decimal('25000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='KWD', value=Decimal('20000'), type=LimitType.WITHDRAWAL),
        Limit(asset_symbol='OMR', value=Decimal('26000'), type=LimitType.WITHDRAWAL),

        Limit(asset_symbol='AED', value=Decimal('250000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='SAR', value=Decimal('255000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='BHD', value=Decimal('25000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='KWD', value=Decimal('20000'), type=LimitType.DEPOSIT),
        Limit(asset_symbol='OMR', value=Decimal('26000'), type=LimitType.DEPOSIT),
    ],
}


OPERATION_TYPE_MAP = {
    LimitType.DEPOSIT: Operation.DEPOSIT,
    LimitType.WITHDRAWAL: Operation.WITHDRAWAL
}


LIMIT_TYPE_MAP = {
    v: k for k, v in OPERATION_TYPE_MAP.items()
}


class UserLimit(NamedTuple):
    asset: str
    total: Decimal
    available: Decimal
    type: LimitType
    interval: LimitInterval
    reset_date: datetime


def get_limit_interval_end(interval: LimitInterval = LimitInterval.WEEK) -> datetime:
    """Get end of limitation interval.

    :param interval:
    :return:
    """
    if interval == LimitInterval.WEEK:
        d = date.today()
        return datetime.combine(
            d + timedelta(days=7 - d.weekday()),
            datetime.min.time()
        )
    elif interval == LimitInterval.DAY:
        return datetime.combine(
            date.today() + timedelta(days=1),
            datetime.min.time()
        )
    elif interval == LimitInterval.MONTH:
        d = date.today() + relativedelta(months=1)
        return d.replace(d=1)
    else:
        raise Exception("Unsupported limit interval `%s`" % interval)


def get_user_limits(user) -> List[UserLimit]:
    """Get payment limits appliable to the user.
    """
    user_limits = []

    # TODO: extend for crypto
    # TODO: timezone handling
    asset = Asset.objects.get(country=user.get_residency_country_code())

    user_assets = [asset.symbol]

    for limit in LIMITS[user.profile.risk_level]:
        if limit.asset_symbol not in user_assets:
            continue

        user_asset = Asset.objects.get(symbol=limit.asset_symbol)

        operation_type = OPERATION_TYPE_MAP[limit.type]
        limit_used = get_limit_used(user, user_asset, operation_type, limit.interval)

        available = limit.value

        if limit_used:
            available = limit.value - limit_used

        user_limits.append(UserLimit(
            asset=user_asset,
            total=limit.value,
            available=available.quantize(
                decimal.Decimal('.1') ** asset.decimals,
                rounding=decimal.ROUND_DOWN
            ),
            type=limit.type,
            reset_date=get_limit_interval_end(limit.interval),
            interval=limit.interval,
        ))

    return user_limits


def get_limit_used(user, asset, operation_type, interval: LimitInterval):
    """Get payment limit used by user specified asset, operation type and interval.
    """
    user_account = UserAccount.objects.for_customer(
        user, asset
    )
    used_limit_qs = Transaction.objects.filter(
        account=user_account,
        operation__type=operation_type,
        operation__status__in=[
            Operation.NEW,
            Operation.HOLD,
            Operation.COMMITTED,
        ]
    )

    today = date.today()
    if interval == LimitInterval.MONTH:
        used_limit_qs = used_limit_qs.filter(
            operation__created_at__year=today.year,
            operation__created_at__month=today.month,
        )
    if interval == LimitInterval.WEEK:
        current_week = today.isocalendar()[1]
        used_limit_qs = used_limit_qs.filter(
            operation__created_at__year=today.year,
            operation__created_at__week=current_week,
        )
    elif interval == LimitInterval.DAY:
        used_limit_qs = used_limit_qs.filter(
            operation__created_at__date=today,
        )

    result = used_limit_qs.aggregate(
        used=Coalesce(Abs(Sum('amount')), V(0))
    )
    return result['used']


MINIMAL_OPERATION_LIMITS = [
    Limit(asset_symbol='AED', value=Decimal(500), type=LimitType.DEPOSIT, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='AED', value=Decimal(500), type=LimitType.WITHDRAWAL, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='KWD', value=Decimal(40), type=LimitType.DEPOSIT, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='KWD', value=Decimal(40), type=LimitType.WITHDRAWAL, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='BHD', value=Decimal(50), type=LimitType.DEPOSIT, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='BHD', value=Decimal(50), type=LimitType.WITHDRAWAL, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='SAR', value=Decimal(500), type=LimitType.DEPOSIT, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='SAR', value=Decimal(500), type=LimitType.WITHDRAWAL, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='OMR', value=Decimal(50), type=LimitType.DEPOSIT, interval=LimitInterval.OPERATION),
    Limit(asset_symbol='OMR', value=Decimal(50), type=LimitType.WITHDRAWAL, interval=LimitInterval.OPERATION),
]

MINIMAL_OPERATION_LIMITS_MAP = {
    (l.type, l.asset_symbol): l.value for l in MINIMAL_OPERATION_LIMITS
}


class OutOfLimitsException(Exception):
    def __init__(self, bottom_limit):
        self.bottom_limit = bottom_limit


def validate_by_limits(operation_type, asset: Asset, amount: Decimal):
    key = (LIMIT_TYPE_MAP[operation_type], asset.symbol)
    min_limit = MINIMAL_OPERATION_LIMITS_MAP.get(key, 0)
    if amount < min_limit:
        raise OutOfLimitsException(min_limit)
