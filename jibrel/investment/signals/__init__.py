from django.dispatch import Signal

investment_submitted = Signal(providing_args=[
    "instance", "asset"
])

waitlist_submitted = Signal(providing_args=[
    "instance"
])
