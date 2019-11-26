from django.conf import settings

from rest_framework.serializers import DecimalField


class AssetPrecisionDecimal(DecimalField):

    """Decimal serializer field with asset precision.

    Should be always defined with `source=*` to get access to sibling asset
    attribute to select precision based on it.

    You should provide `asset_source` or `decimal_places_getter`:

    - `asset_source` may contain original object field with asset instance to get decimals from
    - `decimal_places_getter` may contain serializer method name to use to get actual precision

    This field can be used for serialization only.

    # TODO: support attribute traversing/dot-notation for `real_source`
    """
    real_source = None
    asset_source = None
    decimal_places_getter = None

    def __init__(self, real_source=None, asset_source=None, decimal_places_getter=None, **kwargs):
        self.real_source = real_source
        self.asset_source = asset_source
        self.decimal_places_getter = decimal_places_getter
        assert self.asset_source or self.decimal_places_getter, \
            "`asset_source` or `decimal_places_getter` should be provided to AssetPrecisionDecimal"
        kwargs['max_digits'] = settings.ACCOUNTING_MAX_DIGITS
        kwargs['decimal_places'] = settings.ACCOUNTING_DECIMAL_PLACES
        super().__init__(**kwargs)

    def to_representation(self, value):
        if self.asset_source:
            asset = getattr(value, self.asset_source)
            self.decimal_places = asset.decimals
        else:
            decimal_places = getattr(self.parent, self.decimal_places_getter)(value)
            self.decimal_places = decimal_places
        return super().to_representation(getattr(value, self.real_source))
