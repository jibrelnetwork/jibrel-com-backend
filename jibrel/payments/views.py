from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.api.views import AssetsListAPIView as AssetsListAPIView_
from django_banking.api.views import OperationViewSet as OperationViewSet_
from django_banking.api.views import \
    UploadOperationConfirmationAPIView as UploadOperationConfirmationAPIView_
from django_banking.contrib.card.backend.checkout.api.views import CardDepositAPIView as CardDepositAPIView_, \
    CardChargeAPIView as CardChargeAPIView_, CardTokenizeAPIView as CardTokenizeAPIView_
from django_banking.contrib.wire_transfer.api.views import \
    BankAccountDetailsAPIView as BankAccountDetailsAPIView_
from django_banking.contrib.wire_transfer.api.views import \
    BankAccountListAPIView as BankAccountListAPIView_
from django_banking.contrib.wire_transfer.api.views import \
    WireTransferDepositAPIView as WireTransferDepositAPIView_
from django_banking.models import (
    Account,
    Asset
)
from jibrel.core.permissions import IsKYCVerifiedUser


class UploadOperationConfirmationAPIView(UploadOperationConfirmationAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountListAPIView(BankAccountListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountDetailsAPIView(BankAccountDetailsAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class WireTransferDepositAPIView(WireTransferDepositAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class CardDepositAPIView(CardDepositAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class CardChargeAPIView(CardChargeAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class CardTokenizeAPIView(CardTokenizeAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def post(self, request, *args, **kwargs):
        if not settings.DEBUG:
            raise NotImplementedError()
        return self.create(request, *args, **kwargs)


class OperationViewSet(OperationViewSet_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class AssetsListAPIView(AssetsListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BalanceAPIView(APIView):
    def get(self, request):
        asset = Asset.objects.main_fiat_for_customer(request.user)
        balance = (
            Account.objects.filter(
                useraccount__user=request.user,
                asset=asset
            )
            .with_balances()
            .aggregate(
                total_balance=Coalesce(
                    Sum('balance'),
                    0,
                )
            ).get('total_balance')
        )
        return Response({
            'balance': f'{balance:.2f}',
        })
