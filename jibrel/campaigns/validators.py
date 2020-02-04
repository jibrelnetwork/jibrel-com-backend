from django.core.exceptions import ValidationError

from django_banking.models.assets.enum import AssetType


def asset_validator(value):
    """
    To ensure we never had an security attached to fiat assets
    Actually Asset can be crypto-currency also.
    But it is not scheduled for the further releases yet.
    """
    if value.type != AssetType.TOKEN:
        raise ValidationError('Asset has incorrect type')
