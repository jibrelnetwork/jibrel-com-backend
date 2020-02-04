from uuid import uuid4

from django.db import models
from django.utils.functional import cached_property

from .enum import AssetType
from .managers import AssetManager


class Asset(models.Model):

    """Countable Asset object.

    Used as a reference in other models and outside app.
    """

    TYPE_CHOICES = (
        (AssetType.FIAT, 'Fiat'),
        (AssetType.CRYPTO, 'Cryptocurrency'),
        (AssetType.TOKEN, 'Token'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    type = models.CharField(choices=TYPE_CHOICES, max_length=10)

    name = models.CharField(max_length=128)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    country = models.CharField(max_length=2, null=True)

    decimals = models.SmallIntegerField(default=6)

    objects = AssetManager()

    @cached_property
    def is_digital(self):
        return self.type in (
            AssetType.CRYPTO,
            AssetType.TOKEN
        )

    def __str__(self):
        if self.is_digital:
            return f'{self.symbol}'
        return f'{self.symbol} ({self.country})'
