from rest_framework.permissions import IsAuthenticated

from ccwt.api.views import UploadOperationConfirmationAPIView as UploadOperationConfirmationAPIView_
from ccwt.contrib.wire.api.views import (
    BankAccountListAPIView as BankAccountListAPIView_,
    BankAccountDetailsAPIView as BankAccountDetailsAPIView_,
BankAccountDepositAPIView as BankAccountDepositAPIView_
)
from jibrel.core.permissions import IsKYCVerifiedUser


class UploadOperationConfirmationAPIView(UploadOperationConfirmationAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountListAPIView(BankAccountListAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountDetailsAPIView(BankAccountDetailsAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class BankAccountDepositAPIView(BankAccountDepositAPIView_):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
