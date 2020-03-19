from django.db import models

from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus


class FoloosiChargeQuerySet(models.QuerySet):
    def finished(self, from_date, **kwargs):
        return self.filter(
            created_at__gte=from_date,
            payment_status=FoloosiStatus.CAPTURED
        )
