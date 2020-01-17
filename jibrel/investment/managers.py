from django.db.models.manager import BaseManager

from jibrel.investment.queryset import InvestmentApplicationQuerySet


class InvestmentApplicationManager(BaseManager.from_queryset(InvestmentApplicationQuerySet)):  # type: ignore
    """
    Some methods will be implemented here for sure
    """
