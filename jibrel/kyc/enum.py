class PhoneVerificationStatus:
    PENDING = 'pending'  # Verification created, no valid code has been checked
    APPROVED = 'approved'  # Verification approved, the checked code was valid
    EXPIRED = 'expired'  # The verification was not approved within the valid timeline
    MAX_ATTEMPTS_REACHED = 'max_attempts_reached'  # The user has attempted to verify an invalid code more than 5 times
    CANCELED = 'canceled'  # The verification was canceled by the customer


class KYCSubmissionStatus:
    DRAFT = 'draft'
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class KYCSubmissionType:
    INDIVIDUAL = 'individual'
    BUSINESS = 'business'


class OnfidoResultStatus:
    CLEAR = 'clear'
    CONSIDER = 'consider'
    UNSUPPORTED = 'unsupported'
