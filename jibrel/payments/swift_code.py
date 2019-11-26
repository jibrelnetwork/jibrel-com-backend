import re

from rest_framework.exceptions import ValidationError

from jibrel.kyc.models import BasicKYCSubmission

swift_regexp = re.compile('^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')


def get_swift_country_code(swift_number):
    return swift_number[4:6].upper()


def swift_code_validator(value):
    if swift_regexp.fullmatch(value) is None:
        raise ValidationError("Invalid SWIFT/BIC number")

    country_code = get_swift_country_code(value)
    if country_code not in BasicKYCSubmission.SUPPORTED_COUNTRIES:
        raise ValidationError("Invalid SWIFT/BIC number country")
