from django.db import models
from django.conf import settings


class DecimalField(models.DecimalField):

    """Decimal field with default account precision.

    Use `ACCOUNTING_MAX_DIGITS` and `ACCOUNTING_DECIMAL_PLACES` settings as defaults
    for `max_digits` and `decimal_places` kwargs.
    """

    def __init__(self, **kwargs):
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = settings.ACCOUNTING_MAX_DIGITS
        if 'decimal_places' not in kwargs:
            kwargs['decimal_places'] = settings.ACCOUNTING_DECIMAL_PLACES
        super().__init__(**kwargs)
