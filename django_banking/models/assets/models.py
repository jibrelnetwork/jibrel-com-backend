from uuid import uuid4

from django.db import models

from .enum import AssetType
from .managers import AssetManager


class Asset(models.Model):

    """Countable Asset object.

    Used as a reference in other models and outside app.
    """

    TYPE_CHOICES = (
        (AssetType.FIAT, 'Fiat'),
        (AssetType.CRYPTO, 'Cryptocurrency'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    type = models.CharField(choices=TYPE_CHOICES, max_length=10)

    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    country = models.CharField(max_length=2, null=True)

    decimals = models.SmallIntegerField(default=6)

    objects = AssetManager()

    def __str__(self):
        if self.type == AssetType.CRYPTO:
            return f'{self.symbol}'
        return f'{self.symbol} ({self.country})'
