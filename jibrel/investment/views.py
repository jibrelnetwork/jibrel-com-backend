from django.db.models import Sum, F, Value, Case, When, DecimalField
from django.utils.functional import cached_property
from rest_framework.generics import (
    CreateAPIView,
    get_object_or_404,
    ListAPIView)
from rest_framework.response import Response

from django_banking.core.api.pagination import CustomCursorPagination
from django_banking.models import (
    Asset,
    UserAccount
)
from jibrel.campaigns.models import Offering
from jibrel.core.permissions import IsKYCVerifiedUser
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import InvestmentApplication
from jibrel.investment.serializer import CreateInvestmentApplicationSerializer, InvestmentApplicationSerializer


class InvestmentApplicationAPIView(CreateAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = CreateInvestmentApplicationSerializer
    queryset = InvestmentApplication.objects.all()
    offering_queryset = Offering.objects.all()  # TODO exclude inactive/closed/etc.

    @cached_property
    def offering(self):
        return get_object_or_404(self.offering_queryset, pk=self.kwargs.get('offering_id'))

    def post(self, request, *args, **kwargs):
        self.offering  # raises 404 if offering doesn't exist
        return super(InvestmentApplicationAPIView, self).post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            offering=self.offering,
            user=self.request.user,
            account=UserAccount.objects.for_customer(
                user=self.request.user,
                asset=Asset.objects.main_fiat_for_customer(self.request.user)
            )
        )


class InvestmentApplicationsListAPIView(ListAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = InvestmentApplicationSerializer
    pagination_class = CustomCursorPagination

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_investment = 0

    def get_queryset(self):
        qs = InvestmentApplication.objects.filter(user=self.request.user)
        self.total_investment = qs.annotate(
            current_amount=Case(
                When(status__in=(
                    InvestmentApplicationStatus.HOLD,
                    InvestmentApplicationStatus.COMPLETED
                ), then=F('amount')),
                default=Value(0),
                output_field=DecimalField(),
            ),
        ).aggregate(
            total_investment=Sum('current_amount')
        )['total_investment']
        return qs

    def get_paginated_response(self, data):
        paginated_response = super().get_paginated_response(data)
        paginated_response.data['total_investment'] = str(self.total_investment)
        return paginated_response
