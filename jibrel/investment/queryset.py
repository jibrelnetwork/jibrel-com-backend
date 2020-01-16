from django.db.models import QuerySet

from jibrel.investment.enum import InvestmentApplicationStatus


class InvestmentApplicationQuerySet(QuerySet):
    def active(self):
        return self.filter(
            status__in=(
                InvestmentApplicationStatus.PENDING,
                InvestmentApplicationStatus.HOLD,
                InvestmentApplicationStatus.COMPLETED
            )
        )
