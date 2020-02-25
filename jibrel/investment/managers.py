from django.db.models.manager import BaseManager

from jibrel.investment.queryset import (
    InvestmentApplicationQuerySet,
    InvestmentSubscriptionQuerySet
)


class InvestmentSubscriptionManager(BaseManager.from_queryset(InvestmentSubscriptionQuerySet)):  # type: ignore
    """
    Some methods will be implemented here for sure
    """


class InvestmentApplicationManager(BaseManager.from_queryset(InvestmentApplicationQuerySet)):  # type: ignore
    def get_queryset(self):
        return super(InvestmentApplicationManager, self).get_queryset().exclude_draft()

    def with_draft(self):
        return super(InvestmentApplicationManager, self).get_queryset()
