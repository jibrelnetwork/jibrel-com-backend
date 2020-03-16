from django.dispatch import Signal

foloosi_charge_requested = Signal(providing_args=[
    "instance"
])
foloosi_charge_updated = Signal(providing_args=[
    "instance",
])
