from decimal import Decimal

from django.conf import settings
from pycountry import countries

from django_banking.utils import limit_parser

module_name = __package__.upper()

ALL_COUNTRIES = list(map(lambda country: country.alpha_2, countries))
UNSUPPORTED_COUNTRIES = getattr(settings, f'{module_name}_UNSUPPORTED_COUNTRIES', [])
SUPPORTED_COUNTRIES = [
    x for x in
    getattr(settings, f'{module_name}_SUPPORTED_COUNTRIES', None) or ALL_COUNTRIES
    if x not in UNSUPPORTED_COUNTRIES
]
USER_MODEL = getattr(settings, f'{module_name}_USER_MODEL', getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
ACCOUNTING_MAX_DIGITS = getattr(settings, f'{module_name}_ACCOUNTING_MAX_DIGITS', 16)
ACCOUNTING_DECIMAL_PLACES = getattr(settings, f'{module_name}_ACCOUNTING_DECIMAL_PLACES', 6)

AWS_ACCESS_KEY_ID = getattr(settings, f'{module_name}_AWS_ACCESS_KEY_ID', settings.AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = getattr(settings, f'{module_name}_AWS_SECRET_ACCESS_KEY', settings.AWS_SECRET_ACCESS_KEY)
AWS_STORAGE_BUCKET_NAME = getattr(settings, f'{module_name}_AWS_STORAGE_BUCKET_NAME', settings.AWS_STORAGE_BUCKET_NAME)
AWS_S3_REGION_NAME = getattr(settings, f'{module_name}_AWS_S3_REGION_NAME', settings.AWS_S3_REGION_NAME)
AWS_QUERYSTRING_EXPIRE = getattr(settings, f'{module_name}_AWS_QUERYSTRING_EXPIRE', settings.AWS_QUERYSTRING_EXPIRE)

OPERATION_UPLOAD_LOCATION = getattr(settings, f'{module_name}_OPERATION_UPLOAD_LOCATION', 'operations')

LIMITS = limit_parser(getattr(settings, f'{module_name}_LIMITS', {
    None: [
        {
            'asset_symbol': 'USD',
            'value': Decimal(0),
            'limit_type': 'WITHDRAWAL'
        }
    ]
}))
LIMITS_MINIMAL_OPERATION = limit_parser(getattr(settings, f'{module_name}_LIMITS_MINIMAL_OPERATION', [
    {
        'asset_symbol': 'USD',
        'value': Decimal(1),
        'limit_type': 'DEPOSIT',
        'interval': 'OPERATION'
    }
]))
CARD_BACKEND_ENABLED = f'{module_name}.contrib.card' in settings.INSTALLED_APPS
CRYPTO_BACKEND_ENABLED = f'{module_name}.contrib.crypto' in settings.INSTALLED_APPS
WIRE_TRANSFER_BACKEND_ENABLED = f'{module_name}.contrib.wire_transfer' in settings.INSTALLED_APPS
