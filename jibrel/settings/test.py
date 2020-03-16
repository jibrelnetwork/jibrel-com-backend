from jibrel.settings import *  # NOQA

# Throttle rates is slightly increased to avoid 429 during tests
ANONYMOUS_THROTTLING_LIMIT = 100
USER_THROTTLING_LIMIT = 100
PAYMENTS_THROTTLING_LIMIT = 100

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # NOQA
    'anon': f'{ANONYMOUS_THROTTLING_LIMIT}/min',
    'user': f'{USER_THROTTLING_LIMIT}/min',
    'payments': f'{PAYMENTS_THROTTLING_LIMIT}/min',
}
PROMETHEUS_EXPORT_MIGRATIONS = False
CHECKOUT_PRIVATE_KEY = 'sk_test_9fed4ebe-c99d-4abe-b0b5-b85eb6508373'
CHECKOUT_PUBLIC_KEY = 'pk_test_c109e68b-8100-4007-b457-be9c907c4af1'
CHECKOUT_SANDBOX = True

DJANGO_BANKING_CARD_BACKEND = 'django_banking.contrib.card.backend.foloosi'
