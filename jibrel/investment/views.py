import logging

from django.db import transaction
from django.db.models import (
    Q,
    Sum,
    Value
)
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    get_object_or_404
)
from rest_framework.response import Response

from django_banking.contrib.wire_transfer.models import ColdBankAccount
from django_banking.core.api.pagination import CustomCursorPagination
from django_banking.models import (
    Asset,
    UserAccount
)
from jibrel.campaigns.models import Offering
from jibrel.core.errors import (
    ConflictException,
    ServiceUnavailableException
)
from jibrel.core.permissions import IsKYCVerifiedUser
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import InvestmentApplication
from jibrel.investment.serializer import (
    CreateInvestmentApplicationSerializer,
    InvestmentApplicationSerializer
)
from jibrel.investment.signals import investment_submitted

logger = logging.getLogger(__name__)


class InvestmentApplicationAPIView(GenericAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = CreateInvestmentApplicationSerializer
    queryset = InvestmentApplication.objects.all()
    offering_queryset = Offering.objects.all()  # TODO exclude inactive/closed/etc.

    @cached_property
    def offering(self):
        return get_object_or_404(self.offering_queryset, pk=self.kwargs.get('offering_id'))

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        if self.offering.applications.filter(user=request.user).exists():
            raise ConflictException()  # user already applied to invest in this offering
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = self.perform_create(serializer)
        try:
            bank_account = ColdBankAccount.objects.for_customer(request.user)
        except ColdBankAccount.DoesNotExist:
            logger.exception('Bank Account for accepting payment wasn\'t created in Admin')
            raise ServiceUnavailableException()
        bank_data = {
            'holderName': bank_account.holder_name,
            'ibanNumber': bank_account.iban_number,
            'accountNumber': bank_account.account_number,
            'bankName': bank_account.bank_name,
            'swiftCode': bank_account.swift_code,
            'depositReferenceCode': application.deposit_reference_code,
        }
        investment_submitted.send(
            sender=application.__class__,
            instance=application,
            asset=bank_account.account.asset,
            **bank_data
        )
        return Response(
            {
                'data': bank_data
            },
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        return serializer.save(
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

    def get_queryset(self):
        return InvestmentApplication.objects.filter(user=self.request.user)


class InvestmentApplicationsSummaryAPIView(GenericAPIView):
    def get_queryset(self):
        return InvestmentApplication.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        total_investment = qs.aggregate(total_investment=Coalesce(
            Sum('amount', filter=Q(
                status__in=[
                    InvestmentApplicationStatus.HOLD,
                    InvestmentApplicationStatus.COMPLETED
                ])),
            Value(0))
        )['total_investment']
        return Response({
            'total_investment': "{0:.2f}".format(total_investment)
        })
