from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListCreateAPIView, get_object_or_404, DestroyAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking import logger
from django_banking.api.helpers import sanitize_amount
from django_banking.api.serializers import OperationSerializer
from django_banking.core.utils import get_client_ip
from django_banking.limitations.enum import LimitType
from django_banking.models import Operation, UserAccount, PaymentOperation, Asset
from django_banking.models.accounts.enum import AccountType
from django_banking.models.accounts.exceptions import AccountingException
from django_banking.models.accounts.models import UserRoundingAccount, UserFeeAccount, Account
from django_banking.models.fee.utils import calculate_fee_bank_account_withdrawal
from django_banking.utils import generate_deposit_reference_code
from .serializers import BankAccountSerializer, MaskedBankAccountSerializer, WireTransferDepositSerializer, \
    WireTransferWithdrawalSerializer
from ..models import UserBankAccount, ColdBankAccount, WithdrawalWireTransferOperation, DepositWireTransferOperation
from django_banking.limitations.exceptions import OutOfLimitsException
from django_banking.limitations.utils import validate_by_limits, get_user_limits
from django_banking.models.transactions.enum import OperationType
from ..signals import wire_transfer_withdrawal_requested, wire_transfer_deposit_requested
from ...card.api.mixin import NonAtomicMixin


class BankAccountListAPIView(ListCreateAPIView):

    """User bank accounts list.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBankAccount.objects.filter(user=self.request.user, is_active=True)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BankAccountSerializer
        return MaskedBankAccountSerializer

    def perform_create(self, serializer):
        country_code = self.request.user.get_residency_country_code()
        with transaction.atomic():
            asset = Asset.objects.get(country=country_code)
            account = Account.objects.create(
                asset=asset, type=AccountType.TYPE_NORMAL, strict=False
            )
            serializer.save(user=self.request.user, account=account)


class BankAccountDetailsAPIView(DestroyAPIView):
    """Delete bank account.
    """

    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'bank_account_id'

    def get_queryset(self):
        return UserBankAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class BankAccountDepositAPIView(CreateAPIView):
    """Create bank account deposit request.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WireTransferDepositSerializer

    @transaction.atomic()
    def post(self, request, bank_account_id):  # noqa
        try:
            bank_account = UserBankAccount.objects.get(pk=bank_account_id,
                                                       user=request.user,
                                                       is_active=True)
        except UserBankAccount.DoesNotExist:
            raise NotFound("Bank account with such id not found")

        serializer = self.serializer_class(
            data={

            }
        )
        serializer.is_valid(raise_exception=True)


        try:
            cold_bank_account = ColdBankAccount.objects.for_customer(
                request.user
            )
        except ColdBankAccount.DoesNotExist:
            # Return 500 in case we have no deposit bank account available
            logger.error("No active deposit bank account found for %s country",
                         request.user.get_residency_country_code())
            raise Exception("No active deposit bank account found for %s" % \
                            request.user.get_residency_country_code())

        user_account = UserAccount.objects.for_customer(
            user=request.user, asset=cold_bank_account.account.asset
        )

        reference_code = generate_deposit_reference_code()

        try:
            operation = Operation.objects.create_deposit(
                payment_method_account=cold_bank_account.account,
                user_account=user_account,
                amount=amount,
                references={
                    'user_bank_account_uuid': str(bank_account.uuid),
                    'reference_code': reference_code
                }
            )
            logger.debug(
                "Bank account deposit operation %s created. User account %s, "
                "deposit bank account %s",
                operation, user_account, cold_bank_account
            )
        except AccountingException:
            logger.exception(
                "Accounting exception on create bank account deposit operation"
            )
            raise InvalidException(
                target='amount',
                message='Invalid deposit operation',
            )

        # check limit exceed and reject operation if it was
        user_limits = get_user_limits(request.user)
        logger.debug("Available user limits: %s", user_limits)
        for limit in user_limits:
            if limit.type == LimitType.DEPOSIT and limit.available < 0:
                operation.reject("Deposit limit exceed")
                raise InvalidException(
                    target="amount",
                    message="Deposit limit exceed",
                )
        wire_transfer_deposit_requested.send(
            sender=DepositWireTransferOperation,
            # is it legit?
            instance=operation,
            user_ip_address=get_client_ip(request)
        )
        return Response(
            {
                'id': str(operation.uuid),
                'coldBankAccount': cold_bank_account.bank_account_details,
                'depositReferenceCode': reference_code
            },
            status=status.HTTP_201_CREATED
        )

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class BankAccountWithdrawalAPIView(NonAtomicMixin, APIView):

    """Create bank account withdrawal request.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WireTransferWithdrawalSerializer

    def post(self, request, bank_account_id):
        raise NotImplementedError()


class BankAccountWithdrawalCalculateAPIView(APIView):
    def post(self, request, bank_account_id):
        raise NotImplementedError()
