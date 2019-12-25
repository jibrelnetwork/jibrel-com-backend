from rest_framework.permissions import IsAuthenticated

from django_banking.api.views import (
    UploadOperationConfirmationAPIView as UploadOperationConfirmationAPIView_,
    OperationViewSet as OperationViewSet_,
    PaymentLimitsListAPIView as PaymentLimitsListAPIView_,
    AssetsListAPIView as AssetsListAPIView_
)
from django_banking.contrib.wire_transfer.api.views import (
    BankAccountListAPIView as BankAccountListAPIView_,
    BankAccountDetailsAPIView as BankAccountDetailsAPIView_,
    WireTransferDepositAPIView as WireTransferDepositAPIView_
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


class OperationViewSet(OperationViewSet_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class AssetsListAPIView(AssetsListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class PaymentLimitsListAPIView(PaymentLimitsListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
