from typing import Iterable

from uuid import UUID

from ...models import Price


class PriceNotFoundException(Exception):
    pass


class PriceRepository:
    def get_by_pair_id(self, asset_pair: UUID) -> Price:
        raise NotImplementedError

    def get_by_pairs(self, *asset_pair: UUID) -> Iterable[Price]:
        raise NotImplementedError

    def set(self, price: Price) -> None:
        raise NotImplementedError

    def get_for_user(self, user: UUID, asset_pair: UUID) -> Price:
        raise NotImplementedError

    def set_for_user(self, user: UUID, price: Price) -> None:
        raise NotImplementedError
