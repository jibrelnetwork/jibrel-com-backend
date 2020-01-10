from django.dispatch import Signal

kyc_approved = Signal(providing_args=[
    "instance",
])
kyc_rejected = Signal(providing_args=[
    "instance",
])
kyc_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
