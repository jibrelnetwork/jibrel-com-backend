class ErrorCode:
    INVALID = 'invalid'
    WEAK_PASSWORD = 'weak_password'
    WRONG_PASSWORD = 'wrong_password'
    PHONE_CONFIRMED = 'phone_confirmed'
    EMAIL_CONFIRMED = 'email_confirmed'
    SAME = 'same'


class ValidationError(exceptions.ValidationError):
    default_code = ErrorCode.INVALID
    default_detail = 'This value is not valid'
    status_code = 400

    @classmethod
    def for_field(cls, field, message=None, code=None):
        if message is None:
            message = cls.default_detail
        if code is None:
            code = cls.default_code

        return cls({field: [exceptions.ErrorDetail(message, code)]})
