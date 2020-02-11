from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Exists,
    F,
    OuterRef,
    QuerySet,
    Subquery,
    Value,
    When
)
from django.db.models.functions import Cast

from django_banking.models import Operation
from django_banking.models.transactions.enum import (
    OperationStatus,
    OperationType
)
from jibrel.campaigns.enum import OfferingStatus
from jibrel.core.db.models import Join
from jibrel.investment.enum import (
    InvestmentApplicationPaymentStatus,
    InvestmentApplicationStatus
)
from jibrel.kyc.models import (
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)


class InvestmentSubscriptionQuerySet(QuerySet):
    def with_full_name(self):
        return self.annotate(
            _kyc_i_str=Subquery(
                IndividualKYCSubmission.objects.filter(
                    base_kyc=OuterRef('user__profile__last_kyc_id')
                ).annotate(
                    __str__=Join(*IndividualKYCSubmission.representation_properties)
                ).values_list('__str__')
            ),
            _kyc_b_str=Subquery(
                OrganisationalKYCSubmission.objects.filter(
                    base_kyc=OuterRef('user__profile__last_kyc_id')
                ).annotate(
                    __str__=Join(*OrganisationalKYCSubmission.representation_properties)
                ).values_list('__str__')
            ),
            full_name_=Case(
                When(
                    _kyc_b_str__isnull=False, then=F('_kyc_b_str'),
                ),
                default=F('_kyc_i_str'),
                output_field=CharField(),
            )
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
            deposit_str=Cast('deposit_id', CharField()),
            is_paid=Exists(
                Operation.objects.filter(
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
                    pk=OuterRef('deposit'),
                )
            ),
            is_refunded=Exists(
                Operation.objects.filter(
                    type=OperationType.REFUND,
                    status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED]
                ).annotate(
                    deposit_id=Cast(KeyTextTransform('deposit', 'references'), CharField()),
                ).filter(
                    deposit_id=OuterRef('deposit_str'),
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
