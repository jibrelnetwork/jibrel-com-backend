from rest_framework.throttling import UserRateThrottle


class PaymentsThrottle(UserRateThrottle):
    scope = 'payments'
