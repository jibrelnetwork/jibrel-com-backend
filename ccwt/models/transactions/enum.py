from enum import Enum


class OperationStatus(Enum):
    NEW = 'new'
    HOLD = 'hold'
    COMMITTED = 'committed'
    CANCELLED = 'cancelled'
    DELETED = 'deleted'


class OperationType(Enum):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    BUY = 'buy'
    SELL = 'sell'
    CORRECTION = 'correction'



