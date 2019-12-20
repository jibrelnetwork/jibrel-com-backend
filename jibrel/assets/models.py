from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import (
    Count,
    Q
)
from django.db.models.functions import Concat

from jibrel.accounting import Asset
from jibrel.core.exceptions import NonSupportedCountryException


class AssetPairQuerySet(models.QuerySet):
    def fiat(self):
        return self.filter(base__type=Asset.FIAT, quote__type=Asset.FIAT)

    def crypto(self):
        return self.filter(base__type=Asset.CRYPTO, quote__type=Asset.FIAT)

    def intermediate_crypto(self):
        return self.annotate(
            Count('intermediate_pair_for')
        ).filter(
            base__type=Asset.CRYPTO,
            intermediate_pair_for__count__gt=0,
        )

    def terminal(self):
        return self.annotate(
            Count('intermediate_pair_for')
        ).filter(
            intermediate_pair_for__count=0,
        )

    def with_symbol(self):
        return self.annotate(
            symbol=Concat('base__symbol', 'quote__symbol')
        )

    def for_user(self, user):
        try:
            country = user.get_residency_country_code()
        except NonSupportedCountryException:
            country = None
        query = Q(base__type=Asset.CRYPTO)
        if country is None:
            query &= Q(quote__symbol__iexact=AssetPair.DEFAULT_QUOTE)
        else:
            query &= Q(quote__country__iexact=country)
        return self.filter(query)


class AssetPairManager(models.Manager.from_queryset(AssetPairQuerySet)):  # type: ignore
    def get_queryset(self):
        return super(AssetPairManager, self).get_queryset().with_symbol()


class AssetPair(models.Model):
    """Asset/currency pair traded by Service"""

    DEFAULT_QUOTE = 'USD'

    #: unique identifier
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    #: base asset foreign key, e.g. to BTC
    base = models.ForeignKey(to='core_accounting.Asset', related_name='base_pairs', on_delete=models.CASCADE)
    #: quote asset foreign key, e.g. to AED
    quote = models.ForeignKey(to='core_accounting.Asset', related_name='quote_pairs', on_delete=models.CASCADE)
    #: base asset's decimal places
    base_decimals = models.SmallIntegerField(default=6)
    #: quote asset's decimal places
    quote_decimals = models.SmallIntegerField(default=2)
    #: maximum volume (base) for exchange operation, e.g. 10 BTC; None - unlimited
    base_top_limit = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
        default=Decimal('10000'),
        null=True
    )
    #: minimum volume (base) for exchange operation, e.g. 1 BTC
    base_bottom_limit = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
        default=Decimal('0')
    )
    #: maximum volume (quote) for exchange operation, e.g. 75000 AED; None - unlimited
    quote_top_limit = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
        default=Decimal('10000'),
        null=True
    )
    #: minimum volume (quote) for exchange operation, e.g. 1 AED
    quote_bottom_limit = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
        default=Decimal('1')
    )
    #: fee for selling operation, e.g. 0.035
    sell_fee = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0125'))
    #: fee for buying operation, e.g. 0.035
    buy_fee = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0125'))
    #: intermediate asset (USD) volume for sell price calculation
    sell_intermediate_volume = models.DecimalField(max_digits=10, decimal_places=1, default=Decimal('10000'))
    #: intermediate asset (USD) volume for buy price calculation
    buy_intermediate_volume = models.DecimalField(max_digits=10, decimal_places=1, default=Decimal('10000'))

    intermediate_pairs = models.ManyToManyField(
        to='self',
        related_name='intermediate_pair_for',
        related_query_name='intermediate_pair_for',
        symmetrical=False,
    )

    objects = AssetPairManager()

    def __str__(self) -> str:
        return f'AssetPair<{self.symbol}>'

    def get_symbol(self):
        if hasattr(self, 'symbol'):
            return self.symbol
        return f'{self.base.symbol}{self.quote.symbol}'
