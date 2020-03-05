from django.shortcuts import get_object_or_404
from rest_framework.decorators import permission_classes
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.contrib.crypto.models import (
    UserCryptoAccount,
    UserCryptoDepositAccount
)
from django_banking.core.db.mixin import NonAtomicMixin
from django_banking.models import Asset

from .serializers import CryptoAccountSerializer


class CryptoAccountListAPIView(ListCreateAPIView):
    serializer_class = CryptoAccountSerializer

    def get_queryset(self):
        return UserCryptoAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
        )

    @permission_classes([IsAuthenticated])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class CryptoAccountDetailsAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserCryptoAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CryptoAccountDepositAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id):
        asset = get_object_or_404(Asset, pk=asset_id)

        deposit_account = UserCryptoDepositAccount.objects.for_customer(
            user=request.user, asset=asset
        )
        return Response({
            "address": deposit_account.address,
        })


class CryptoAccountWithdrawalAPIView(NonAtomicMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        raise NotImplementedError()


class CryptoWithdrawalConfirmationView(NonAtomicMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        raise NotImplementedError()


class CryptoWithdrawalCalculateAPIView(APIView):
    def post(self, request, asset_id):
        raise NotImplementedError()
