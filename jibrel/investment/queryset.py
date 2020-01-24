from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Exists,
    OuterRef,
    QuerySet,
    Value,
    When
)
from django.db.models.functions import Cast

from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationStatus, OperationType
from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.enum import (
    InvestmentApplicationPaymentStatus,
    InvestmentApplicationStatus
)


class InvestmentApplicationQuerySet(QuerySet):
    def active(self):
        return self.filter(
            status__in=(
                InvestmentApplicationStatus.PENDING,
                InvestmentApplicationStatus.HOLD,
                InvestmentApplicationStatus.COMPLETED
            )
        )

    def with_payment_status(self):
        return self.annotate(
            deposit_uuid=Cast('deposit_id', CharField()),
            is_paid=Exists(
                Operation.objects.filter(
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                    pk=OuterRef('deposit'),
                )
            ),
            is_refunded=Exists(
                Operation.objects.annotate(
                    deposit_id=Cast('references__deposit', CharField()),
                ).filter(
                    type=OperationType.REFUND,
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                    deposit_id=OuterRef('deposit_uuid'),
                )
            ),
            payment_status=Case(
                When(
                    is_paid=True, is_refunded=False, then=Value(InvestmentApplicationPaymentStatus.PAID),
                ),
                When(
                    is_paid=True, is_refunded=True, then=Value(InvestmentApplicationPaymentStatus.REFUND),
                ),
                default=Value(InvestmentApplicationPaymentStatus.NOT_PAID),
                output_field=CharField(),
            )
        )

    def with_enqueued_to_cancel(self):
        return self.annotate(
            enqueued_to_cancel=Case(
                When(
                    offering__status__in=[OfferingStatus.CLEARING, OfferingStatus.CANCELED],
                    status=InvestmentApplicationStatus.PENDING,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
        )

    def with_enqueued_to_refund(self):
        return self.annotate(
            enqueued_to_refund=Case(
                When(
                    offering__status=OfferingStatus.CANCELED,
                    status=InvestmentApplicationStatus.HOLD,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        )
