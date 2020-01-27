from django.dispatch import Signal

deposit_refunded = Signal(providing_args=[
    "instance", 'deposit'
])
