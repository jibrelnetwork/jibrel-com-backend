import time
from decimal import Decimal

from factory import DjangoModelFactory, post_generation

from jibrel.assets import AssetPair
from jibrel.exchanges import Price, price_repository


class AssetPairFactory(DjangoModelFactory):
    class Meta:
        model = AssetPair

    @post_generation
    def price(self, create, extracted, **kwargs):
        price_repository.set(
            Price(
                pair_id=self.pk,
                sell=Decimal(9),
                buy=Decimal(11),
                ts=int(time.time()),
            )
        )
