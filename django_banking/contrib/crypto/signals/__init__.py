from django.dispatch import Signal

crypto_deposit_approved = Signal(providing_args=[
    "instance",
])
crypto_deposit_rejected = Signal(providing_args=[
    "instance",
])
crypto_deposit_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
crypto_withdrawal_approved = Signal(providing_args=[
    "instance",
])
crypto_withdrawal_rejected = Signal(providing_args=[
    "instance",
])
crypto_withdrawal_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
