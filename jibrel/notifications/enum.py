class ExternalServiceCallLogActionType:
    PHONE_VERIFICATION = 1
    PHONE_CHECK_VERIFICATION = 2
    SEND_MAIL = 3


class ExternalServiceCallLogInitiatorType:
    USER = 'user'
    ANON = 'anonymous'
    SYSTEM = 'system'


class ExternalServiceCallLogStatus:
    SUCCESS = 'success'
    ERROR = 'error'
