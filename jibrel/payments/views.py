from checkout_sdk.payments.responses import (
    PaymentPending,
    PaymentProcessed
)
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.api.views import AssetsListAPIView as AssetsListAPIView_
from django_banking.api.views import OperationViewSet as OperationViewSet_
from django_banking.api.views import \
    UploadOperationConfirmationAPIView as UploadOperationConfirmationAPIView_
from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus
from django_banking.contrib.card.backend.checkout.models import CheckoutCharge
from django_banking.contrib.card.backend.checkout.signals import charge_updated
from django_banking.contrib.card.models import DepositCardOperation
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
from jibrel.payments.permissions import CheckoutHMACSignature


class UploadOperationConfirmationAPIView(UploadOperationConfirmationAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountListAPIView(BankAccountListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountDetailsAPIView(BankAccountDetailsAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class WireTransferDepositAPIView(WireTransferDepositAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


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


class CheckoutWebhook(APIView):
    """
    Make sure web server is ready to accept requests from that IP addresses
    https://docs.checkout.com/docs/webhooks#section-ip-addresses
    """
    permission_classes = [CheckoutHMACSignature]

    def post(self, request):
        data = request.data['data']
        reference_code = data['reference']
        # TODO find user and deposit by refernce code
        if data['status'] == CheckoutStatus.PENDING:
            payment = PaymentPending(request)
        else:
            payment = PaymentProcessed(request)

        try:
            charge = CheckoutCharge.objects.get(charge_id=payment.id)
            charge.update_status(payment.status)
        except ObjectDoesNotExist:
            # actually this fallback only possible in case of lost some data during request
            # for example in case
            # TODO please note that deposit with reference_code also can be lost, but should happen never
            deposit = DepositCardOperation.objects.get(
                references__reference_code=reference_code
            )
            charge = CheckoutCharge.objects.create(
                user=deposit.card_account.user,
                payment=payment,
                operation=deposit
            )

        charge_updated(charge, sender=charge.__class__)
        return Response()
