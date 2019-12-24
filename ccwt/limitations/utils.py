import decimal
from datetime import date, timedelta, datetime
from typing import List

from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce, Abs

from .data import UserLimit, OPERATION_TYPE_MAP, LIMIT_TYPE_MAP
from .enum import LimitInterval
from ccwt.models import Transaction, UserAccount, Asset
from ccwt.models.transactions.enum import OperationStatus
from .exceptions import OutOfLimitsException


# TODO: move to db
LIMITS = {
    None: []
}
MINIMAL_OPERATION_LIMITS = []
MINIMAL_OPERATION_LIMITS_MAP = {
    (l.type, l.asset_symbol): l.value for l in MINIMAL_OPERATION_LIMITS
}


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
            OperationStatus.NEW,
            OperationStatus.HOLD,
            OperationStatus.COMMITTED,
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
        used=Coalesce(Abs(Sum('amount')), Value(0))
    )
    return result['used']


def validate_by_limits(operation_type, asset: Asset, amount: decimal.Decimal):
    key = (LIMIT_TYPE_MAP[operation_type], asset.symbol)
    min_limit = MINIMAL_OPERATION_LIMITS_MAP.get(key, 0)
    if amount < min_limit:
        raise OutOfLimitsException(min_limit)
