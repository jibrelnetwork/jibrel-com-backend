from django.db import models

from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus


class FoloosiChargeQuerySet(models.QuerySet):
    def finished(self, from_date, **kwargs):
        # Success operation is not finished cuz it still can be refunded
        return self.filter(
            created_at__gte=from_date,
            charge_id__isnull=False,
            payment_status__in=(
                FoloosiStatus.DECLINED,
                FoloosiStatus.REFUND
            )
        )
