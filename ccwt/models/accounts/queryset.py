from django.db import models
from django.db.models import Sum, Q, Value
from django.db.models.functions import Coalesce

from ccwt.models.assets.enum import AssetType
from ccwt.models.transactions.enum import OperationType, OperationStatus


class AccountQuerySet(models.QuerySet):

    def with_balances(self):
        return self.annotate(
           balance=Coalesce(
               Sum(
                   'transaction__amount',
                   filter=Q(
                       transaction__operation__type=OperationType.DEPOSIT,
                       transaction__operation__status=OperationStatus.COMMITTED,
                   ) | Q(
                       transaction__operation__type=OperationType.WITHDRAWAL,
                       transaction__operation__status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                   ) | Q(
                       transaction__operation__type=OperationType.BUY,
                       transaction__account__asset__type=AssetType.CRYPTO,
                       transaction__operation__status=OperationStatus.COMMITTED,
                   ) | Q(
                       transaction__operation__type=OperationType.BUY,
                       transaction__account__asset__type=AssetType.FIAT,
                       transaction__operation__status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                   ) | Q(
                       transaction__operation__type=OperationType.SELL,
                       asset__type=AssetType.FIAT,
                       transaction__operation__status=OperationStatus.COMMITTED,
                   ) | Q(
                       transaction__operation__type=OperationType.SELL,
                       asset__type=AssetType.CRYPTO,
                       transaction__operation__status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                   )
               ),
               Value(0)
           )
        )
