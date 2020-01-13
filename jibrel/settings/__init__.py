import os
from datetime import timedelta
from typing import Optional

from decouple import (
    Csv,
    config
)

# environment variables
ENVIRONMENT = os.environ['ENVIRONMENT']
DJANGO_SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']
MAIN_DB_HOST = os.environ['MAIN_DB_HOST']
MAIN_DB_PORT = os.environ['MAIN_DB_PORT']
MAIN_DB_NAME = os.environ['MAIN_DB_NAME']
MAIN_DB_USER = os.environ['MAIN_DB_USER']
MAIN_DB_USER_PASSWORD = os.environ['MAIN_DB_USER_PASSWORD']

SENTRY_DSN = os.getenv('SENTRY_DSN', '')

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_API_URL = os.environ['TWILIO_API_URL']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_VERIFICATION_SERVICE_SID = os.environ['TWILIO_VERIFICATION_SERVICE_SID']
TWILIO_REQUEST_TIMEOUT = int(os.environ.get('TWILIO_REQUEST_TIMEOUT', '5'))
MAILGUN_API_KEY = os.environ['MAILGUN_API_KEY']
MAILGUN_API_URL = os.environ['MAILGUN_API_URL']
MAILGUN_SENDER_DOMAIN = os.environ['MAILGUN_SENDER_DOMAIN']
MAILGUN_FROM_EMAIL = os.environ['MAILGUN_FROM_EMAIL']

SEND_VERIFICATION_TIME_LIMIT = int(os.environ['SEND_VERIFICATION_TIME_LIMIT'])
FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT = int(os.environ['FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT'])
FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT = int(os.environ['FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT'])
VERIFICATION_SESSION_LIFETIME = int(os.environ['VERIFICATION_SESSION_LIFETIME'])
VERIFY_EMAIL_TOKEN_LIFETIME = int(os.environ['VERIFY_EMAIL_TOKEN_LIFETIME'])
VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT = int(os.environ['VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT'])
VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT = int(os.environ['VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT'])
VERIFY_EMAIL_SEND_TOKEN_TIMEOUT = int(os.environ['VERIFY_EMAIL_SEND_TOKEN_TIMEOUT'])
FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME = config('FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME', cast=int)
FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT = config('FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT', cast=int)
FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT = config('FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT', cast=int)
FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT = config('FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT', cast=int)

UPLOAD_KYC_DOCUMENT_COUNT = config('UPLOAD_KYC_DOCUMENT_COUNT', cast=int, default=20)
UPLOAD_KYC_DOCUMENT_TIME_LIMIT = config('UPLOAD_KYC_DOCUMENT_TIME_LIMIT', cast=int, default=3600)

ONFIDO_API_KEY = config('ONFIDO_API_KEY')
ONFIDO_API_URL = config('ONFIDO_API_URL', default='https://api.onfido.com/v2')
ONFIDO_DEFAULT_RETRY_DELAY = config('ONFIDO_DEFAULT_RETRY_DELAY', cast=int, default=10)
ONFIDO_MAX_RETIES = config('ONFIDO_MAX_RETIES', cast=int, default=10)
ONFIDO_COLLECT_RESULTS_SCHEDULE = config('ONFIDO_COLLECT_RESULTS_SCHEDULE', cast=int, default=1200)

# S3 and file storing
AWS_S3_LOCATION_PREFIX = config('AWS_S3_LOCATION_PREFIX', default='')
KYC_DATA_LOCATION = config('KYC_DATA_LOCATION', default='kyc')
OPERATION_UPLOAD_LOCATION = config('OPERATION_UPLOAD_LOCATION', default='operations')
if AWS_S3_LOCATION_PREFIX:
    KYC_DATA_LOCATION = f'{AWS_S3_LOCATION_PREFIX}/{KYC_DATA_LOCATION}'
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME')
AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
AWS_QUERYSTRING_EXPIRE = config('AWS_QUERYSTRING_EXPIRE', default=60 * 15, cast=int)
AWS_AUTO_CREATE_BUCKET = config('AWS_AUTO_CREATE_BUCKET', default=False)
AWS_DEFAULT_ACL = None
S3_USE_SIGV4 = True
AWS_S3_SIGNATURE_VERSION = 's3v4'


TAP_SECRET = config('TAP_SECRET', default="sk_test_XKokBfNWv6FIYuTMg5sLPjhJ")
TAP_PUB = config('TAP_PUB', default="pk_test_EtHFV4BuPQokJT6jiROls87Y")
TAP_KEY = config(
    'TAP_KEY',
    default=(
        "-----BEGIN PUBLIC KEY----- MIIBIDANBgkqhkiG9w0BAQEFAAOCAQ0AMIIBCAKCAQEA21z"
        "7Vcrrraiksj31If5K f7XGv6QNoHP7SRPjxxbxAnPrrI597NI683pHIaIgb0UNaOUggU6FYN+w"
        "+tBc1Mwk 1aOBsM8Ok6W0SsFxpa+Jt3VdOfF4iBw7k4sdd+EP5PfaiFdbrndRcCmV32mb87+I "
        "cuzDRxyqgl1Bx0dCPqmw0YCCWTuM+LXN60MHr56M5WO7J64AXn5YVzspZkon4Leg d9QbycUC7"
        "7e/MUmhZL5QcGvXaBYWS5Lw5ROhjMYrLK15f4gWoYLtDcUTtMEEEtef EF4tus0Vx7XTrHa9vG"
        "bH9qUmH5F9HUkYOUX+UaFj7qVdfaR/VecB5xCwrt5ixV6y 3QIBEQ== -----END PUBLIC KE"
        "Y-----"
    )
)

DOMAIN_NAME = config('DOMAIN_NAME')
domain = config('DOMAIN_NAME')
subdomains = config('SUBDOMAINS', cast=Csv(str))

SESSION_COOKIE_DOMAIN: Optional[str] = f'.{domain}'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = None

CSRF_COOKIE_DOMAIN: Optional[str] = f'.{domain}'
CSRF_COOKIE_HTTPONLY = False

if domain == 'localhost':
    SESSION_COOKIE_DOMAIN = None
    CSRF_COOKIE_DOMAIN = None

CSRF_TRUSTED_ORIGINS = [domain]

for sub in subdomains:
    CSRF_TRUSTED_ORIGINS.append(
        f'{sub}.{domain}'
    )

schemas = ['http', 'https']

CORS_ORIGIN_WHITELIST = [f'{s}://{domain}' for s in schemas]
CORS_ALLOW_CREDENTIALS = True

for sub in subdomains:
    for schema in schemas:
        CORS_ORIGIN_WHITELIST.append(
            f'{schema}://{sub}.{domain}'
        )

LANGUAGE_COOKIE_NAME = os.getenv('LANGUAGE_COOKIE_NAME', 'lang')

ALPHA_VANTAGE_API_URL = config('ALPHA_VANTAGE_API_URL', default='https://www.alphavantage.co')
PUBLIC_KRAKEN_API_URL = config('PUBLIC_KRAKEN_API_URL', default='https://api.kraken.com/0/public')

PRIVATE_KRAKEN_API_URI = config('PRIVATE_KRAKEN_API_URL', default='https://api.kraken.com')
PRIVATE_KRAKEN_API_KEY = config('PRIVATE_KRAKEN_API_KEY')
PRIVATE_KRAKEN_SIGN_KEY = config('PRIVATE_KRAKEN_SIGN_KEY')
LIVE_MARKET_TRADING = config('LIVE_MARKET_TRADING', default=False, cast=bool)
KRAKEN_UPDATE_BALANCE_SCHEDULE = config('KRAKEN_UPDATE_BALANCE_SCHEDULE', default=10, cast=int)
MARKET_BALANCE_CHECKING_SCHEDULE = config('MARKET_BALANCE_CHECKING_SCHEDULE', default=15, cast=int)

RATES_CACHE_CONTROL_TIMEOUT = config('RATES_CACHE_CONTROL_TIMEOUT', default=300, cast=int)
EXCHANGE_OFFER_LIFETIME = config('EXCHANGE_OFFER_LIFETIME', default=60, cast=int)
EXCHANGE_PRICE_FOR_USER_LIFETIME = config('EXCHANGE_PRICE_LIFETIME', default=300, cast=int)
REDIS_HOST = config('REDIS_HOST')
REDIS_PORT = config('REDIS_PORT')
REDIS_DB = config('REDIS_DB', cast=int, default=0)
REDIS_PASSWORD = config('REDIS_PASSWORD')
EXCHANGE_PRICES_RECALCULATION_SCHEDULE = config('EXCHANGE_PRICES_RECALCULATION_SCHEDULE', 15, cast=int)
EXCHANGE_FETCH_TRANSACTIONS_SCHEDULE = config('EXCHANGE_FETCH_TRANSACTIONS_SCHEDULE', 10, cast=int)
EXCHANGE_FETCH_TRADES_SCHEDULE = config('EXCHANGE_FETCH_TRADES_SCHEDULE', 30, cast=int)

TAP_CHARGE_PROCESSING_SCHEDULE = config('TAP_CHARGE_PROCESSING_SCHEDULE', default=30, cast=int)


#  server environment, possible choices now: develop, production_new
server_env = config('SERVER_ENV', default='production_new')

SERVER_ENV = {
    'production_new': 'production',
    'production': 'production',
    'stage': 'staging',
    'staging': 'staging',
    'develop': 'develop',
}.get(server_env, 'production')

# accounting settings
ACCOUNTING_MAX_DIGITS = 16
ACCOUNTING_DECIMAL_PLACES = 6

# django settings
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

DEBUG = ENVIRONMENT == 'development'
SECRET_KEY = DJANGO_SECRET_KEY
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv(str))

try:
    with open(os.path.join(BASE_DIR, '../../version.txt')) as fp:
        VERSION = fp.read().strip()
except Exception:  # noqa
    VERSION = 'dev'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_banking',
    'django_banking.contrib.wire_transfer',

    'jibrel.authentication',
    'jibrel.notifications',
    'jibrel.kyc',
    'jibrel.campaigns',
    'jibrel.payments',

    'django_celery_results',
    'corsheaders',
    'constance',
]

CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'


CONSTANCE_REDIS_CONNECTION = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'password': REDIS_PASSWORD,
    'db': REDIS_DB,
}

CONSTANCE_CONFIG = {
    'TRADING_IS_ACTIVE': (True, 'Trading integration with the Market is active for now')
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jibrel.urls'

WSGI_APPLICATION = 'jibrel.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': MAIN_DB_NAME,
        'USER': MAIN_DB_USER,
        'PASSWORD': MAIN_DB_USER_PASSWORD,
        'HOST': MAIN_DB_HOST,
        'PORT': MAIN_DB_PORT,
    }
}

AUTH_USER_MODEL = 'authentication.User'

TIME_ZONE = 'UTC'
USE_TZ = True

STATIC_URL = '/static/'

ANONYMOUS_THROTTLING_LIMIT = config('ANONYMOUS_THROTTLING_LIMIT', cast=int, default=20)
USER_THROTTLING_LIMIT = config('USER_THROTTLING_LIMIT', cast=int, default=50)
PAYMENTS_THROTTLING_LIMIT = config('PAYMENTS_THROTTLING_LIMIT', cast=int, default=10)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'jibrel.core.permissions.IsConfirmedUser',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'jibrel.core.throttling.PaymentsThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': f'{ANONYMOUS_THROTTLING_LIMIT}/min',
        'user': f'{USER_THROTTLING_LIMIT}/min',
        'payments': f'{PAYMENTS_THROTTLING_LIMIT}/min',
    },
    'EXCEPTION_HANDLER': 'jibrel.core.rest_framework.exception_handler'
}

CELERY_RESULT_BACKEND = os.environ['CELERY_RESULT_BACKEND']

EMAIL_BACKEND = 'jibrel.notifications.email.EmailBackend'
DEFAULT_FROM_EMAIL = MAILGUN_FROM_EMAIL if MAILGUN_FROM_EMAIL else f'admin@{domain}'

ANYMAIL = {
    'MAILGUN_API_KEY': MAILGUN_API_KEY,
    'MAILGUN_SENDER_DOMAIN': MAILGUN_SENDER_DOMAIN,
    'MAILGUN_API_URL': MAILGUN_API_URL,

}

EMAIL_TEMPLATES_DIR = config('EMAIL_TEMPLATES_DIR')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, 'templates'), EMAIL_TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CORS_ALLOW_CREDENTIALS = True

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()]
    )

CELERY_WORKER_HIJACK_ROOT_LOGGER = False
LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(message)s',
        }
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'jibrel.exchanges.tasks': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'jibrel.exchanges.fiat_price_calculator': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'jibrel.payments.tap': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'jibrel.payments.tap.base': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}

DJANGO_BANKING_USER_MODEL = 'authentication.User'

KYC_ADMIN_NOTIFICATION_RECIPIENT = config('KYC_ADMIN_NOTIFICATION_RECIPIENT')
KYC_ADMIN_NOTIFICATION_PERIOD = config('KYC_ADMIN_NOTIFICATION_PERIOD', cast=int, default=1)

CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'send_admin_new_kyc_notification': {
        'task': 'jibrel.kyc.task.send_admin_new_kyc_notification',
        'schedule': timedelta(hours=KYC_ADMIN_NOTIFICATION_PERIOD)
    }
}
