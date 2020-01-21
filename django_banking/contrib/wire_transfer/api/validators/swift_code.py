import re

from rest_framework.exceptions import ValidationError

from django_banking.settings import SUPPORTED_COUNTRIES

swift_regexp = re.compile('^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')


def get_swift_country_code(swift_number):
    return swift_number[4:6].upper()


def is_valid_swift_code(value):
    return swift_regexp.fullmatch(value) is not None


def swift_code_validator(value):
    if not is_valid_swift_code(value):
        raise ValidationError("Invalid SWIFT/BIC number")

    country_code = get_swift_country_code(value)
    if country_code not in SUPPORTED_COUNTRIES:
        raise ValidationError("Invalid SWIFT/BIC number country")
