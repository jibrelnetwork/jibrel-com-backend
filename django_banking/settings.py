from django.conf import settings
from pycountry import countries

__prefix__ = __package__.upper()

ALL_COUNTRIES = list(map(lambda country: country.alpha_2, countries))
UNSUPPORTED_COUNTRIES = getattr(settings, f'{__prefix__}_UNSUPPORTED_COUNTRIES', [])
SUPPORTED_COUNTRIES = [
    x for x in
    getattr(settings, f'{__prefix__}_SUPPORTED_COUNTRIES', None) or ALL_COUNTRIES
    if x not in UNSUPPORTED_COUNTRIES
]
USER_MODEL = getattr(settings, f'{__prefix__}_USER_MODEL', getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
ACCOUNTING_MAX_DIGITS = getattr(settings, f'{__prefix__}_ACCOUNTING_MAX_DIGITS', 16)
ACCOUNTING_DECIMAL_PLACES = getattr(settings, f'{__prefix__}_ACCOUNTING_DECIMAL_PLACES', 6)

AWS_ACCESS_KEY_ID = getattr(settings, f'{__prefix__}_AWS_ACCESS_KEY_ID', settings.AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = getattr(settings, f'{__prefix__}_AWS_SECRET_ACCESS_KEY', settings.AWS_SECRET_ACCESS_KEY)
AWS_STORAGE_BUCKET_NAME = getattr(settings, f'{__prefix__}_AWS_STORAGE_BUCKET_NAME', settings.AWS_STORAGE_BUCKET_NAME)
AWS_S3_REGION_NAME = getattr(settings, f'{__prefix__}_AWS_S3_REGION_NAME', settings.AWS_S3_REGION_NAME)
AWS_QUERYSTRING_EXPIRE = getattr(settings, f'{__prefix__}_AWS_QUERYSTRING_EXPIRE', settings.AWS_QUERYSTRING_EXPIRE)

OPERATION_UPLOAD_LOCATION = getattr(settings, f'{__prefix__}_OPERATION_UPLOAD_LOCATION', 'operations')
