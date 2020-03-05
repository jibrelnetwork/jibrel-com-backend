class OperationStatus:
    NEW = 'new'
    THREEDS = 'action_required'
    HOLD = 'hold'
    COMMITTED = 'committed'
    CANCELLED = 'cancelled'
    DELETED = 'deleted'
    ERROR = 'failed'


class OperationType:
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    BUY = 'buy'
    SELL = 'sell'
    CORRECTION = 'correction'
    REFUND = 'refund'


class OperationMethod:
    CARD = 'card'
    WIRE_TRANSFER = 'wire_transfer'
    DIGITAL = 'digital'
    OTHER = 'other'
