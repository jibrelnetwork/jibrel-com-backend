from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.api.views import AssetsListAPIView as AssetsListAPIView_
from django_banking.api.views import OperationViewSet as OperationViewSet_
from django_banking.api.views import \
    UploadOperationConfirmationAPIView as UploadOperationConfirmationAPIView_
from django_banking.contrib.card.backend.checkout.enum import (
    CheckoutStatus,
    WebhookType
)
from django_banking.contrib.card.backend.checkout.models import CheckoutCharge
from django_banking.contrib.card.backend.checkout.signals import (
    checkout_charge_updated
)
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
from jibrel.core.errors import ConflictException
from jibrel.core.permissions import IsKYCVerifiedUser
from jibrel.payments.permissions import CheckoutHMACSignature
from jibrel.payments.serializers import (
    FoloosiChargeSerializer,
    InvestmentOperationSerializer
)
from jibrel.payments.tasks import (
    checkout_update,
    foloosi_update
)


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
    serializer_class = InvestmentOperationSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_card and instance.is_pending:
            card_account_type = instance.references["card_account"]["type"]
            if card_account_type == 'foloosi':
                foloosi_update.delay(instance.pk)
            elif card_account_type == 'checkout':
                checkout_update.delay(instance.pk, instance.charge.pk,)

        serializer = self.get_serializer(instance)
        response = Response(serializer.data)
        if not response.exception:
            response.data = {
                'data': response.data
            }
        return response

    @action(methods=['POST'], detail=True, url_path='deposit/card')
    def update_charge(self, request, *args, **kwargs):
        operation = self.get_object()

        if not operation.charge:
            raise ConflictException()

        serializer = FoloosiChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        foloosi_update.delay(
            deposit_id=operation.pk,
            charge_id=serializer.data['chargeId']
        )
        return Response(status=status.HTTP_202_ACCEPTED)


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
        webhook_type = request.data['type']
        charge_id = data['id']
        charge = CheckoutCharge.objects.filter(charge_id=charge_id).first()
        if not charge or webhook_type == WebhookType.PAYMENT_REFUNDED:
            checkout_update(reference_code, charge_id)
        else:
            status = {
                WebhookType.PAYMENT_APPROVED: CheckoutStatus.AUTHORIZED,
                WebhookType.PAYMENT_PENDING: CheckoutStatus.PENDING,
                WebhookType.PAYMENT_DECLINED: CheckoutStatus.DECLINED,
                WebhookType.PAYMENT_EXPIRED: CheckoutStatus.DECLINED,
                WebhookType.PAYMENT_VOIDED: CheckoutStatus.VOIDED,
                WebhookType.PAYMENT_CANCELED: CheckoutStatus.CANCELLED,
                WebhookType.PAYMENT_CAPTURED: CheckoutStatus.CAPTURED,
                WebhookType.PAYMENT_CAPTURE_DECLINED: CheckoutStatus.DECLINED,
                WebhookType.PAYMENT_PAID: CheckoutStatus.PAID
            }.get(webhook_type) or CheckoutStatus.DECLINED
            charge.update_status(status)
            checkout_charge_updated.send(instance=charge, sender=charge.__class__)
        return Response()
