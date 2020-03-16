from django.dispatch import Signal

checkout_charge_requested = Signal(providing_args=[
    "instance"
])
checkout_charge_updated = Signal(providing_args=[
    "instance",
])
