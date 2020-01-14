class InvestmentApplicationStatus:
    PENDING = 'pending'
    HOLD = 'hold'  # hold funds for the further processing
    COMPLETED = 'completed'
    CANCELED = 'canceled'  # canceled by user
    EXPIRED = 'expired'  # not enough funds
