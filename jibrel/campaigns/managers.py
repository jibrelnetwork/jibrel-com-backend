from django.db.models.manager import BaseManager

from jibrel.campaigns.queryset import OfferingQuerySet


class OfferingManager(BaseManager.from_queryset(OfferingQuerySet)):  # type: ignore
    """
    Some methods will be implemented here for sure
    """
