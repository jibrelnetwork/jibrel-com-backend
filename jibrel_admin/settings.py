import os

from decouple import Csv, config

from jibrel.settings import (  # NOQA
    CONSTANCE_BACKEND,
    CONSTANCE_CONFIG,
    CONSTANCE_REDIS_CONNECTION,
    SUPPORTED_COUNTRIES
)

# environment variables
ENVIRONMENT = os.environ['ENVIRONMENT']
DJANGO_SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DJANGO_ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split()
ADMIN_DB_HOST = os.environ['ADMIN_DB_HOST']
ADMIN_DB_PORT = os.environ['ADMIN_DB_PORT']
ADMIN_DB_NAME = os.environ['ADMIN_DB_NAME']
ADMIN_DB_USER = os.environ['ADMIN_DB_USER']
ADMIN_DB_USER_PASSWORD = os.environ['ADMIN_DB_USER_PASSWORD']
MAIN_DB_HOST = os.environ['MAIN_DB_HOST']
MAIN_DB_PORT = os.environ['MAIN_DB_PORT']
MAIN_DB_NAME = os.environ['MAIN_DB_NAME']
MAIN_DB_USER = os.environ['MAIN_DB_USER']
MAIN_DB_USER_PASSWORD = os.environ['MAIN_DB_USER_PASSWORD']
IS_TESTING = os.environ.get('IS_TESTING', False)

CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']

# S3 and file storing
AWS_S3_LOCATION_PREFIX = os.getenv('AWS_S3_LOCATION_PREFIX', '')
KYC_DATA_LOCATION = os.getenv('KYC_DATA_LOCATION', 'kyc')
if AWS_S3_LOCATION_PREFIX:
    KYC_DATA_LOCATION = f'{AWS_S3_LOCATION_PREFIX}/{KYC_DATA_LOCATION}'
OPERATION_UPLOAD_LOCATION = os.environ.get('OPERATION_UPLOAD_LOCATION', 'operations')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)
AWS_QUERYSTRING_EXPIRE = os.getenv('AWS_QUERYSTRING_EXPIRE', 60 * 15)
KYC_DATA_USE_S3 = config('KYC_DATA_USE_S3', default=True, cast=bool)

AWS_DEFAULT_ACL = None
S3_USE_SIGV4 = True
AWS_S3_SIGNATURE_VERSION = 's3v4'

EXCHANGE_PRICE_FOR_USER_LIFETIME = int(os.getenv('EXCHANGE_PRICE_LIFETIME', 300))
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = DJANGO_SECRET_KEY

DEBUG = ENVIRONMENT == 'development'

ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv(str))

try:
    with open(os.path.join(BASE_DIR, 'version.txt')) as fp:
        VERSION = fp.read().strip()
except Exception:  # noqa
    VERSION = 'dev'

# Application definition

INSTALLED_APPS = [
    'admin_tools',
    'admin_tools.dashboard',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_select2',
    'constance',
    'django_object_actions',
    'nested_admin',

    'jibrel.authentication',
    'jibrel.kyc',
    # required by pytest
    'jibrel.notifications',
    'jibrel_admin',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jibrel_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, 'templates'),],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'admin_tools.template_loaders.Loader',
            ],
        },
    },
]

WSGI_APPLICATION = 'jibrel_admin.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': ADMIN_DB_NAME,
        'USER': ADMIN_DB_USER,
        'PASSWORD': ADMIN_DB_USER_PASSWORD,
        'HOST': ADMIN_DB_HOST,
        'PORT': ADMIN_DB_PORT,
    },

    MAIN_DB_NAME: {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': MAIN_DB_NAME,
        'USER': MAIN_DB_USER,
        'PASSWORD': MAIN_DB_USER_PASSWORD,
        'HOST': MAIN_DB_HOST,
        'PORT': MAIN_DB_PORT,
    }
}

DATABASE_ROUTERS = ['jibrel_admin.db.router.MainDBRouter']

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.environ['STATIC_ROOT']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        # Custom handler which we will use with logger 'django'.
        # We want errors/warnings to be logged when DEBUG=False
        'console_on_not_debug': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'logging.StreamHandler',
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'console_on_not_debug'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

ADMIN_TOOLS_INDEX_DASHBOARD = 'jibrel_admin.dashboards.IndexDashboard'


ACCOUNTING_MAX_DIGITS = 16
ACCOUNTING_DECIMAL_PLACES = 6
