from django.db.models import QuerySet, Exists, OuterRef, Case, When, Value, CharField

from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationStatus
from jibrel.investment.enum import InvestmentApplicationStatus, InvestmentApplicationPaymentStatus


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
            is_paid=Exists(
                Operation.objects.filter(
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                    pk=OuterRef('deposit'),
                )
            ),
            is_refunded=Exists(
                Operation.objects.filter(
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                    pk=OuterRef('refund'),
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
