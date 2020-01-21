class InvestmentApplicationStatus:
    PENDING = 'pending'
    HOLD = 'hold'  # hold funds for the further processing
    COMPLETED = 'completed'
    CANCELED = 'canceled'  # canceled by user
    EXPIRED = 'expired'  # not enough funds
    ERROR = 'error'  # funds has arrived but it is not meets a minimum investing amount


class InvestmentApplicationPaymentStatus:
    PAID = 'paid'
    NOT_PAID = 'not_paid'
    REFUND = 'refund'
