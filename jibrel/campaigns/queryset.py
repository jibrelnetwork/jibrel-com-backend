from django.db.models import QuerySet
from django.utils import timezone

from jibrel.campaigns.enum import OfferingStatus


class OfferingQuerySet(QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            status=OfferingStatus.ACTIVE,
            date_start__lte=now,
            date_end__gt=now,
        )
