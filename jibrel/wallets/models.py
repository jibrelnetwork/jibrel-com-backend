import uuid

from django.db import models

from jibrel.wallets.utils import public_key_to_address


class Wallet(models.Model):
    """
    Wallet metadata for mobile App
    """
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    mnemonic = models.CharField(max_length=500)
    public_key = models.CharField(max_length=500, unique=True)
    address = models.CharField(max_length=42, unique=True, editable=False)
    derivation_path = models.CharField(max_length=500)
    user = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    version_number = models.PositiveIntegerField(default=0)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.version_number += 1
        self.address = public_key_to_address(self.public_key)
        super().save(*args, **kwargs)

