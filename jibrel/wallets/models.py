import uuid

from django.db import models
from django.db.models import Q

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

    @classmethod
    def search(cls, q):
        criteria = Q(address__startswith=q) | Q(user__email__startswith=q) | Q(user__profile__phones__number__startswith=q)
        wallets = cls.objects.filter(criteria, deleted=False)
        def item(wallet: Wallet):
            profile = wallet.user.profile
            data = {
                'name': '{} {}.'.format(profile.first_name, profile.last_name[0]),
                'email': wallet.user.email,
                'kycStatus': profile.kyc_status,
                'phoneNumber': profile.phone.number,
                'address': wallet.address,
                'whitelist': []  #FIXME! fix later when whitelist will be implemented
            }
            return data
        return [item(w) for w in wallets]


class NotableAddresses(models.Model):
    """
    List of named blockchain addresses
    """
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=42, unique=True)


def get_addresses_names(address_list):
    notable = NotableAddresses.objects.filter(address__in=address_list).values('name', 'address')
    wallets_objs = Wallet.objects.select_related('user').filter(address__in=address_list, deleted=False)
    wallets = [{'name': '{} {}'.format(w.user.profile.first_name, w.user.profile.last_name), 'address': w.address}
               for w in wallets_objs]
    return list(notable) + wallets
