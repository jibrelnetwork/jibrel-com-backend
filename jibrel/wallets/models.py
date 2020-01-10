from django.db import models


class Wallet(models.Model):
    """
    Wallet metadata for mobile App
    """
    uid = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    mnemonic = models.CharField(max_length=500)
    public_key = models.CharField(max_length=500)
    derivation_path = models.CharField(max_length=500)
    user = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    version_number = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        self.version_number += 1
        super().save(*args, **kwargs)




