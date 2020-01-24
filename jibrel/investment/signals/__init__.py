from django.dispatch import Signal

investment_submitted = Signal(providing_args=[
    "instance", "asset"
])
