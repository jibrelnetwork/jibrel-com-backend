from rest_framework import serializers

from jibrel.core.errors import ErrorCode
from jibrel.core.validators import (
    PasswordValidator,
    PhoneNumberValidator
)


class PasswordField(serializers.CharField):
    default_error_messages = {
        ErrorCode.WEAK_PASSWORD: 'Password is too weak'
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 100)
        super(PasswordField, self).__init__(**kwargs)

    default_validators = [
        PasswordValidator()
    ]


class PhoneNumberField(serializers.CharField):
    default_error_messages = {
        'invalid': 'Please enter a valid phone number.'
    }

    def __init__(self, **kwargs):
        validators = kwargs.get('validators', [])
        validators.append(PhoneNumberValidator())
        kwargs['validators'] = validators
        super().__init__(**kwargs)

    def to_representation(self, value):
        value = super(PhoneNumberField, self).to_representation(value)
        return value and value[-4:]


# FIXME
class DateField(serializers.DateField):
    default_error_messages = {
        'invalid': 'Invalid date.'
    }
