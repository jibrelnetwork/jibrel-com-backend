class ProfileKYCStatus:
    PENDING = 'pending'
    UNVERIFIED = 'unverified'
    VERIFIED = 'verified'
    ADVANCED = 'advanced'


class PhoneStatus:
    UNCONFIRMED = 'unconfirmed'
    CODE_REQUESTED = 'code_requested'
    CODE_SENT = 'code_sent'
    CODE_SUBMITTED = 'code_submitted'
    CODE_INCORRECT = 'code_incorrect'
    EXPIRED = 'expired'
    MAX_ATTEMPTS_REACHED = 'max_attempts_reached'
    VERIFIED = 'verified'


class OTTType:
    EMAIL_VERIFICATION = 1
    PASSWORD_RESET_ACTIVATE = 2
    PASSWORD_RESET_COMPLETE = 3
    CRYPTO_WITHDRAWAL_CONFIRMATION = 4
