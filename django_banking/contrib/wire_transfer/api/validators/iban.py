from rest_framework.serializers import ValidationError

from django_banking import logger
from django_banking.contrib.wire_transfer.api.validators.swift_code import (
    get_swift_country_code
)
from django_banking.contrib.wire_transfer.iban import (
    generate_iban_check_digits,
    valid_iban
)
from django_banking.settings import SUPPORTED_COUNTRIES


def iban_validator(value):
    if not valid_iban(value) or generate_iban_check_digits(value) != value[2:4]:
        raise ValidationError("Invalid IBAN")

    country_code = value[:2].upper()
    if country_code not in SUPPORTED_COUNTRIES:
        raise ValidationError("Unsupported IBAN country")


class IbanValidator:
    requires_context = True

    def __call__(self, value, serializer_field):
        country = get_swift_country_code(
            serializer_field.parent.initial_data.get('swiftCode', '')
        )
        if country != 'OM':
            iban_validator(value)
        else:
            logger.debug("Skip IBAN validation for OMAN banks")
