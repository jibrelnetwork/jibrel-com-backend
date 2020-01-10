from django.dispatch import Signal

password_reset_requested = Signal(providing_args=[
    "instance", "user_ip_address"
])
