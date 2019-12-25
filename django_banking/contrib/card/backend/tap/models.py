from uuid import uuid4

from django.db import models

from django_banking.models import Operation


class TapCharge(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, null=True)

    charge_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


