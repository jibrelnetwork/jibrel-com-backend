from enum import Enum


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
