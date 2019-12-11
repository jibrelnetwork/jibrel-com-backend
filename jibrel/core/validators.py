from rest_framework import serializers

from jibrel.core.errors import ErrorCode
from .utils import (
    is_strong_password,
    is_valid_phone_number
)


class PasswordValidator:
    def __init__(self, required_score=3):
        self.required_score = required_score
        self.base = None

    def set_context(self, base: serializers.Field):
        self.base = base

    def get_user_inputs(self):
        password_field_name = self.base.field_name
        all_data = self.base.root.initial_data
        return [
            value for field, value in all_data.items() if field != password_field_name
        ]

    def __call__(self, password):
        if not is_strong_password(password, self.get_user_inputs(), required_score=self.required_score):
            self.base.fail(ErrorCode.WEAK_PASSWORD)


class PhoneNumberValidator:
    def set_context(self, base: serializers.Field):
        self.base = base

    def __call__(self, number):
        if not is_valid_phone_number(number):
            self.base.fail('invalid')

