import logging
import string

from rest_framework.serializers import ValidationError

from jibrel.kyc.models import BasicKYCSubmission
from jibrel.payments.swift_code import get_swift_country_code

logger = logging.getLogger(__name__)


LETTERS = {ord(d): str(i) for i, d in enumerate(string.digits + string.ascii_uppercase)}


def _number_iban(iban):
    return (iban[4:] + iban[:4]).translate(LETTERS)


def generate_iban_check_digits(iban):
    number_iban = _number_iban(iban[:2] + '00' + iban[4:])
    return '{:0>2}'.format(98 - (int(number_iban) % 97))


def valid_iban(iban):
    return int(_number_iban(iban)) % 97 == 1


def iban_validator(value):
    if not valid_iban(value) or generate_iban_check_digits(value) != value[2:4]:
        raise ValidationError("Invalid IBAN")

    country_code = value[:2].upper()
    if country_code not in BasicKYCSubmission.SUPPORTED_COUNTRIES:
        raise ValidationError("Unsupported IBAN country")


class IbanValidator:
    def __call__(self, value):
        if self.country != 'OM':
            iban_validator(value)
        else:
            logger.debug("Skip IBAN validation for OMAN banks")

    def set_context(self, serializer_field):
        self.country = get_swift_country_code(
            serializer_field.parent.initial_data.get('swiftCode', '')
        )
