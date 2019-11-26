from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict

from rest_framework.exceptions import APIException


class ErrorCode(Enum):
    INVALID = 'Invalid'
    REQUIRED = 'Required'
    NOT_NULL = 'NotNull'
    WEAK_PASSWORD = 'WeakPassword'
    UNIQUE = 'Unique'
    TOO_LONG = 'TooLong'
    WRONG_PASSWORD = 'WrongPassword'
    PHONE_CONFIRMED = 'PhoneConfirmed'
    EMAIL_CONFIRMED = 'EmailConfirmed'
    TIMEOUT = 'Timeout'


@dataclass
class Error:
    code: ErrorCode
    message: str
    target: str

    def serialize(self) -> Dict[str, str]:
        dct = asdict(self)
        dct['code'] = dct['code'].value
        return dct


class CoinMENAException(BaseException):
    default_code = ErrorCode.INVALID
    default_message = 'This value is not valid'
    status_code = 400

    def __init__(self, target, message=None, code=None):
        if code is None:
            code = self.default_code
        if message is None:
            message = self.default_message
        self.errors = [Error(code=code, message=message, target=target)]

    @classmethod
    def from_errors(cls, *errors):
        exc = cls.__new__(cls)
        exc.errors = list(errors)
        return exc


class UniqueException(CoinMENAException):
    default_code = ErrorCode.UNIQUE
    default_message = 'Should be unique'


class WeakPasswordException(CoinMENAException):
    default_code = ErrorCode.WEAK_PASSWORD
    default_message = 'Password too weak'


class WrongPasswordException(CoinMENAException):
    default_code = ErrorCode.WRONG_PASSWORD
    default_message = 'Wrong password'


class PhoneVerifiedException(CoinMENAException):
    default_code = ErrorCode.PHONE_CONFIRMED
    default_message = 'Phone already confirmed'


class EmailVerifiedException(CoinMENAException):
    default_code = ErrorCode.EMAIL_CONFIRMED
    default_message = 'Email already confirmed'


class InvalidException(CoinMENAException):
    pass


class ConflictException(APIException):
    status_code = 409
    default_detail = 'Action not permitted'


class ServiceUnavailableException(APIException):
    status_code = 503
