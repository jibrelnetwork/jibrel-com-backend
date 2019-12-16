from rest_framework import serializers

from jibrel.core.errors import ErrorCode
from .utils import (
    is_strong_password,
    is_valid_phone_number
)


class PasswordValidator:
    requires_context = True

    def __init__(self, required_score=3):
        self.required_score = required_score

    def __call__(self, password, serializer_field):
        password_field_name = serializer_field.field_name
        all_data = serializer_field.root.initial_data
        user_inputs = [
            value for field, value in all_data.items() if field != password_field_name
        ]

        if not is_strong_password(password, user_inputs, required_score=self.required_score):
            serializer_field.fail(ErrorCode.WEAK_PASSWORD)


class PhoneNumberValidator:
    requires_context = True

    def __call__(self, number, serializer_field):
        if not is_valid_phone_number(number):
            serializer_field.fail('invalid')

