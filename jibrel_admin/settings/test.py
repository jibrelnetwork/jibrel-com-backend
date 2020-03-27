from jibrel_admin.settings import *  # NOQA

MIDDLEWARE = [
    element for element in MIDDLEWARE if element not in [   # NOQA
        'whitenoise.middleware.WhiteNoiseMiddleware'
    ]
]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
PROMETHEUS_EXPORT_MIGRATIONS = False
OTT_DEBUG = True
