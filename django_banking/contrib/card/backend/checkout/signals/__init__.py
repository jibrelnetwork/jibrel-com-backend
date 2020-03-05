from django.dispatch import Signal

charge_requested = Signal(providing_args=[
    "instance"
])
charge_updated = Signal(providing_args=[
    "instance",
])
