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
