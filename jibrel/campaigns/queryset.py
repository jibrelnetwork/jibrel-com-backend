from django.conf import settings
from django.db.models import (
    Count,
    DecimalField,
    IntegerField,
    OuterRef,
    QuerySet,
    Subquery,
    Sum
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from jibrel.campaigns.enum import OfferingStatus


class OfferingQuerySet(QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            status=OfferingStatus.ACTIVE,
            date_start__lte=now,
            date_end__gt=now,
        )

    def with_application_statistics(self):
        from jibrel.investment.models import InvestmentApplication
        from jibrel.investment.enum import InvestmentApplicationStatus

        def get_subquery(status):
            kwargs = {'offering': OuterRef('pk')}
            if status is not None:
                kwargs['status'] = status
            return Coalesce(
                Subquery(
                    InvestmentApplication.objects.all()
                        .filter(**kwargs)
                        .values('offering')
                        .order_by()
                        .annotate(cnt=Count('*'))
                        .values('cnt')[:1],
                ),
                0,
                output_field=IntegerField()
            )

        return self.annotate(
            total_applications_count_=get_subquery(None),
            pending_applications_count_=get_subquery(InvestmentApplicationStatus.PENDING),
            hold_applications_count_=get_subquery(InvestmentApplicationStatus.HOLD),
            completed_applications_count_=get_subquery(InvestmentApplicationStatus.COMPLETED),
            canceled_applications_count_=get_subquery(InvestmentApplicationStatus.CANCELED),
        )

    def with_money_statistics(self):
        from jibrel.investment.models import InvestmentApplication
        from jibrel.investment.enum import InvestmentApplicationStatus

        def get_subquery(status):
            kwargs = {'offering': OuterRef('pk')}
            if status is not None:
                kwargs['status'] = status
            return Coalesce(
                Subquery(
                    InvestmentApplication.objects.all()
                        .filter(**kwargs)
                        .values('offering')
                        .order_by()
                        .annotate(sum=Sum('amount'))
                        .values('sum')[:1],
                ),
                0,
                output_field=DecimalField(
                    max_digits=settings.ACCOUNTING_MAX_DIGITS,
                    decimal_places=2,
                )
            )
        return self.annotate(
            total_money_sum_=get_subquery(None),
            pending_money_sum_=get_subquery(InvestmentApplicationStatus.PENDING),
            hold_money_sum_=get_subquery(InvestmentApplicationStatus.HOLD),
            completed_money_sum_=get_subquery(InvestmentApplicationStatus.COMPLETED),
            canceled_money_sum_=get_subquery(InvestmentApplicationStatus.CANCELED),
        )
