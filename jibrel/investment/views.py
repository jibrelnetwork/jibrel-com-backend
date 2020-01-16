import logging

from django.utils.functional import cached_property
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    get_object_or_404
)
from rest_framework.response import Response

from django_banking.contrib.wire_transfer.models import ColdBankAccount
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
from jibrel.investment.models import InvestmentApplication
from jibrel.investment.serializer import InvestmentApplicationSerializer

logger = logging.getLogger(__name__)


class InvestmentApplicationAPIView(GenericAPIView):
    permission_classes = [IsKYCVerifiedUser]
    serializer_class = InvestmentApplicationSerializer
    queryset = InvestmentApplication.objects.all()
    offering_queryset = Offering.objects.all()  # TODO exclude inactive/closed/etc.

    @cached_property
    def offering(self):
        return get_object_or_404(self.offering_queryset, pk=self.kwargs.get('offering_id'))

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
        return Response(
            {
                'data': {
                    'holderName': bank_account.holder_name,
                    'ibanNumber': bank_account.iban_number,
                    'accountNumber': bank_account.account_number,
                    'bankName': bank_account.bank_name,
                    'swiftCode': bank_account.swift_code,
                    'depositReferenceCode': application.deposit_reference_code,
                }
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
