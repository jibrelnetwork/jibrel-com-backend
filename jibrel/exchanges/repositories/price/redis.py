import json
from typing import AnyStr, Iterable, Optional
from uuid import UUID

import redis
from django.utils import timezone

from ...models import Price
from .abstract import PriceNotFoundException
from .abstract import PriceRepository as AbstractPriceRepository


class PriceRepository(AbstractPriceRepository):
    def __init__(self, connection: redis.Redis, price_for_user_lifetime: int):
        self._conn = connection
        self._price_for_user_lifetime = price_for_user_lifetime

    def get_by_pair_id(self, asset_pair_id: UUID) -> Price:
        raw_data = self._conn.get(
            str(asset_pair_id)
        )
        return self._deserialize_one_price(raw_data)

    def get_by_pairs(self, *asset_pairs: UUID) -> Iterable[Price]:
        raw_data_set = self._conn.mget(
            *map(str, asset_pairs)
        )
        return (
            self._deserialize_one_price(raw_data)
            for raw_data in raw_data_set
        )

    def _deserialize_one_price(self, data: Optional[AnyStr]) -> Price:
        if not data:
            raise PriceNotFoundException
        deserialized = json.loads(data)
        return Price.deserialize(deserialized)

    def set(self, price: Price) -> None:
        self._conn.set(
            str(price.pair_id),
            json.dumps(price.serialize())
        )

    def get_for_user(self, user_id: UUID, asset_pair_id: UUID) -> Price:
        raw_data = self._conn.get(
            f'{user_id}__{asset_pair_id}'
        )
        price = self._deserialize_one_price(raw_data)
        if (timezone.now().timestamp() - price.ts) > self._price_for_user_lifetime:
            self._conn.delete(
                f'{user_id}__{asset_pair_id}'
            )
            raise PriceNotFoundException
        return price

    def set_for_user(self, user: UUID, price: Price) -> None:
        serialized = price.serialize()
        serialized['ts'] = int(timezone.now().timestamp())
        self._conn.set(
            f'{user}__{price.pair_id}',
            json.dumps(serialized)
        )
