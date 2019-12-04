from rest_framework import serializers

from jibrel.core.errors import ErrorCode
from jibrel.core.validators import PasswordValidator


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
