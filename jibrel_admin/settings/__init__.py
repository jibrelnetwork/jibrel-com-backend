import os

from decouple import config

from jibrel.settings import *  # NOQA # to avoid forgotten imports

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# environment variables
ADMIN_DB_HOST = os.environ['ADMIN_DB_HOST']
ADMIN_DB_PORT = os.environ['ADMIN_DB_PORT']
ADMIN_DB_NAME = os.environ['ADMIN_DB_NAME']
ADMIN_DB_USER = os.environ['ADMIN_DB_USER']
ADMIN_DB_USER_PASSWORD = os.environ['ADMIN_DB_USER_PASSWORD']

IS_TESTING = os.environ.get('IS_TESTING', False)


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
    'django_object_actions',
    'nested_admin',
    'django_banking',
    'django_banking.contrib.wire_transfer',

    'jibrel.authentication',
    'jibrel.notifications',
    'jibrel.kyc',
    'jibrel.campaigns',
    'jibrel.payments',
    'jibrel.investment',
    'jibrel.wallets',
    # required by pytest
    'django_celery_results',
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

AUTH_USER_MODEL = 'auth.User'
ROOT_URLCONF = 'jibrel_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, 'templates'), EMAIL_TEMPLATES_DIR],  # NOQA
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

    MAIN_DB_NAME: {  # NOQA
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': MAIN_DB_NAME,  # NOQA
        'USER': MAIN_DB_USER,  # NOQA
        'PASSWORD': MAIN_DB_USER_PASSWORD,  # NOQA
        'HOST': MAIN_DB_HOST,  # NOQA
        'PORT': MAIN_DB_PORT,  # NOQA
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

OTT_DEBUG = config('OTT_DEBUG', default=False, cast=bool)

DOCU_SIGN_API_HOST = config('DOCU_SIGN_API_HOST', default='https://demo.docusign.net/restapi')
DOCU_SIGN_ACCOUNT_ID = config('DOCU_SIGN_ACCOUNT_ID')
DOCU_SIGN_RETURN_URL_TEMPLATE = f'https://investor.{DOMAIN_NAME}/application/{{application_id}}'
