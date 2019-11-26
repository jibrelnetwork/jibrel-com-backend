from __future__ import annotations

import dataclasses
from decimal import Decimal

from django.conf import settings
from django.db import models
from typing import Optional
from uuid import UUID


@dataclasses.dataclass
class Price:
    #: asset pair unique identifier
    pair_id: UUID
    #: sell price
    sell: Decimal
    #: buy price
    buy: Decimal
    #: unix timestamp
    ts: int
    #: if Price object is for supported pair like ETH/AED this value will be Price object for ETH/USD pair
    intermediate_crypto: Optional[Price] = None
    #: if Price object is for supported pair like ETH/AED this value will be Price object for USD/AED pair
    intermediate_fiat: Optional[Price] = None

    def serialize(self) -> dict:
        return {
            'pair_id': str(self.pair_id),
            'sell': str(self.sell),
            'buy': str(self.buy),
            'ts': self.ts,
            'intermediate_crypto': self.intermediate_crypto and self.intermediate_crypto.serialize(),
            'intermediate_fiat': self.intermediate_fiat and self.intermediate_fiat.serialize(),
        }

    @classmethod
    def deserialize(cls, price_dict: dict) -> 'Price':
        kwargs = dict(
            pair_id=UUID(price_dict['pair_id']),
            sell=Decimal(price_dict['sell']),
            buy=Decimal(price_dict['buy']),
            ts=int(price_dict['ts']),
        )
        intermediate_crypto = price_dict.get('intermediate_crypto')
        if intermediate_crypto:
            kwargs['intermediate_crypto'] = cls.deserialize(intermediate_crypto)
        intermediate_fiat = price_dict.get('intermediate_fiat')
        if intermediate_fiat:
            kwargs['intermediate_fiat'] = cls.deserialize(intermediate_fiat)
        return cls(
            **kwargs
        )


class MarketBalanceLimit(models.Model):
    asset = models.OneToOneField(to='core_accounting.Asset', on_delete=models.CASCADE)
    alert_value = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
    )
    raise_value = models.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS,
        decimal_places=settings.ACCOUNTING_DECIMAL_PLACES,
    )
