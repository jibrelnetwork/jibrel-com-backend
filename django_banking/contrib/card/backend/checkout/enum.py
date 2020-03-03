class CheckoutStatus:
    AUTHORIZED = 'authorized'
    PENDING = 'pending'
    VERIFIED = 'card verified'
    CAPTURED = 'captured'
    DECLINED = 'declined'
    PAID = 'paid'


class ChargeStatus:
    NEW = 'new'
    PREPARING = 'preparing'
    VALIDATING = 'validating'
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'
