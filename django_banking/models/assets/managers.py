from django.db import models
from django.db.models import Q

from .enum import AssetType


class AssetManager(models.Manager):
    def for_customer(self, user) -> models.QuerySet:
        user_country = user.get_residency_country_code()
        return self.filter(
            Q(type=AssetType.CRYPTO) | Q(type=AssetType.FIAT, country=user_country)
        )

    def main_fiat_for_customer(self, user) -> 'Asset':
        user_country = user.get_residency_country_code()
        return self.filter(
            Q(country=user_country) | Q(country__isnull=True),
            type=AssetType.FIAT,
        ).order_by('country').last()
