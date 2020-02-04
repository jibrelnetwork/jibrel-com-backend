from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListCreateAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.models import Asset
from django_banking.models.accounts.enum import AccountType
from django_banking.models.accounts.models import Account

from ...card.api.mixin import NonAtomicMixin
from ..models import UserBankAccount
from .serializers import (
    BankAccountSerializer,
    MaskedBankAccountSerializer,
    WireTransferDepositSerializer,
    WireTransferWithdrawalSerializer
)


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
        with transaction.atomic():
            asset = Asset.objects.main_fiat_for_customer(self.request.user)
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


class WireTransferDepositAPIView(NonAtomicMixin, CreateAPIView):
    """Create bank account deposit request.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WireTransferDepositSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        bank_account_id = context['request'].resolver_match.kwargs['bank_account_id']
        try:
            user_bank_account = UserBankAccount.objects.get(pk=bank_account_id,
                                                       user=context['request'].user,
                                                       is_active=True)
        except UserBankAccount.DoesNotExist:
            raise NotFound("Bank account with such id not found")
        context.update({
            'user_bank_account': user_bank_account
        })
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # get serializer again to get all fields
        serializer = self.get_serializer(serializer.instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class WireTransferWithdrawalAPIView(NonAtomicMixin, APIView):

    """Create bank account withdrawal request.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WireTransferWithdrawalSerializer

    def post(self, request, bank_account_id):
        raise NotImplementedError()


class BankAccountWithdrawalCalculateAPIView(APIView):
    def post(self, request, bank_account_id):
        raise NotImplementedError()
