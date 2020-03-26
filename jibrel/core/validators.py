import magic
from django.core.files import File

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


class FileTypeValidator:
    requires_context = True

    def __init__(self, *types):
        if len(types) == 0:
            raise TypeError('At least one argument required')
        self.types = set(types)

    def __call__(self, file: File, serializer_field):
        magic_bytes = file.read(1024)
        file.seek(0)
        mime_type = magic.from_buffer(magic_bytes, mime=True)
        if mime_type not in self.types:
            serializer_field.fail(ErrorCode.WRONG_TYPE)


class FileSizeValidator:
    requires_context = True

    def __init__(self, min_size=None, max_size=None):
        if min_size is None and max_size is None:
            raise TypeError('At least one argument required')
        self.min_size = min_size or 0
        self.max_size = max_size

    def __call__(self, file: File, serializer_field):
        if file.size < self.min_size:
            serializer_field.fail(ErrorCode.MIN_SIZE, min_size=self.min_size)
        if self.max_size is not None and file.size > self.max_size:
            serializer_field.fail(ErrorCode.MAX_SIZE, max_size=self.max_size)
