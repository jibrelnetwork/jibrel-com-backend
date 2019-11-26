from django.conf import settings

from .abstract import PriceRepository, PriceNotFoundException  # noqa
from .redis import PriceRepository as RedisPriceRepository
import redis

price_repository = RedisPriceRepository(
    redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    ),
    settings.EXCHANGE_PRICE_FOR_USER_LIFETIME,
)

all = [
    'PriceRepository',
    'PriceNotFoundException',
    'price_repository',
]
