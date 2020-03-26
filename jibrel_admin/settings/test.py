from jibrel_admin.settings import *  # NOQA

MIDDLEWARE = [
    element for element in MIDDLEWARE if element not in [   # NOQA
        'whitenoise.middleware.WhiteNoiseMiddleware'
    ]
]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
PROMETHEUS_EXPORT_MIGRATIONS = False
OTT_DEBUG = True

CHECKOUT_PRIVATE_KEY = 'sk_test_9fed4ebe-c99d-4abe-b0b5-b85eb6508373'
CHECKOUT_PUBLIC_KEY = 'pk_test_c109e68b-8100-4007-b457-be9c907c4af1'
