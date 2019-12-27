class OperationStatus:
    NEW = 'new'
    HOLD = 'hold'
    COMMITTED = 'committed'
    CANCELLED = 'cancelled'
    DELETED = 'deleted'


class OperationType:
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    BUY = 'buy'
    SELL = 'sell'
    CORRECTION = 'correction'
