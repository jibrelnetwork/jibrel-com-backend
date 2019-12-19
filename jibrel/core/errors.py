from rest_framework import exceptions
from rest_framework.settings import api_settings


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


class WrongPasswordException(ValidationError):
    default_code = ErrorCode.WRONG_PASSWORD
    default_detail = 'Wrong password'


class PhoneVerifiedException(ValidationError):
    default_code = ErrorCode.PHONE_CONFIRMED
    default_detail = 'Phone already confirmed'


class EmailVerifiedException(ValidationError):
    default_code = ErrorCode.EMAIL_CONFIRMED
    default_detail = 'Email already confirmed'


class InvalidException(ValidationError):
    def __init__(self, target=api_settings.NON_FIELD_ERRORS_KEY, message=None, code=None):
        if message is None:
            message = self.default_detail
        if code is None:
            code = self.default_code

        super().__init__({target: [exceptions.ErrorDetail(message, code)]})


class APIException(exceptions.APIException):

    def __init__(self, detail=None, code=None, data=None):
        super().__init__(detail, code)
        self.data = data


class ConflictException(APIException):
    status_code = 409
    default_detail = 'Action not permitted'


class ServiceUnavailableException(APIException):
    status_code = 503
