from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking import logger
from django_banking.api.helpers import sanitize_amount
from django_banking.api.serializers import OperationSerializer
from django_banking.contrib.crypto.models import CryptoAccount, DepositCryptoAccount, WithdrawalCryptoOperation
from django_banking.core.utils import get_client_ip
from django_banking.models import UserAccount, Operation, Asset, PaymentOperation
from django_banking.models.accounts.exceptions import AccountingException
from django_banking.models.accounts.models import RoundingUserAccount, FeeUserAccount
from django_banking.models.fee.utils import calculate_fee_crypto_withdrawal
from django_banking.models.transactions.enum import OperationStatus
from .serializers import CryptoAccountSerializer
from jibrel.core.errors import InvalidException
from ...card.api.mixin import NonAtomicMixin
from ...wire_transfer.signals import wire_transfer_withdrawal_requested


class CryptoAccountListAPIView(ListCreateAPIView):
    serializer_class = CryptoAccountSerializer

    def get_queryset(self):
        return CryptoAccount.objects.filter(user=self.request.user, is_active=True)

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
        return CryptoAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CryptoAccountDepositAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id):
        asset = get_object_or_404(Asset, pk=asset_id)

        deposit_account = DepositCryptoAccount.objects.for_customer(
            user=request.user, asset=asset
        )
        return Response({
            "address": deposit_account.address,
        })


class CryptoAccountWithdrawalAPIView(NonAtomicMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_metadata(self, base_asset, quote_asset, amount):
        asset_pair = AssetPair.objects.get(
            base=base_asset,
            quote=quote_asset,
        )
        price = price_repository.get_by_pair_id(asset_pair.pk)
        return {
            'total_price': {
                'asset_pair_id': str(asset_pair.pk),
                'base_asset_id': str(asset_pair.base.pk),
                'quote_asset_id': str(asset_pair.quote.pk),
                'sell_price': str(price.sell),
                'buy_price': str(price.buy),
                'total': str(price.sell * amount)
            }
        }

    def post(self, request, pk):
        crypto_account = CryptoAccount.objects.get(pk=pk)

        try:
            amount = request.data['amount']
        except (KeyError, TypeError):
            raise InvalidException(target='amount', message='Invalid amount')

        amount = sanitize_amount(
            amount,
            decimal_places=crypto_account.account.asset.decimals
        )

        withdrawal_account = crypto_account.account
        user_account = UserAccount.objects.for_customer(
            user=request.user, asset=withdrawal_account.asset
        )
        fee_account = FeeUserAccount.objects.for_customer(
            user=request.user, asset=withdrawal_account.asset
        )
        fee = calculate_fee_crypto_withdrawal(amount=amount, asset=withdrawal_account.asset)
        fee_amount = fee.rounded
        amount -= fee_amount
        rounding_account = RoundingUserAccount.objects.for_customer(request.user, fee_account.asset)
        try:
            operation = Operation.objects.create_withdrawal(
                user_account=user_account,
                payment_method_account=withdrawal_account,
                amount=amount,
                fee_account=fee_account,
                fee_amount=fee_amount,
                rounding_account=rounding_account,
                rounding_amount=fee.remainder,
                references={
                    'confirmation_token': token.hex
                },
                hold=False,
                metadata=self.get_metadata(
                    base_asset=withdrawal_account.asset,
                    quote_asset=Asset.objects.main_fiat_for_customer(request.user),
                    amount=amount,
                )
            )
            wire_transfer_withdrawal_requested.send(
                sender=WithdrawalCryptoOperation,
                instance=operation,
                user_ip_address=get_client_ip(request),
                address=crypto_account.address,
            )

            serializer = OperationSerializer(
                PaymentOperation.objects.with_amounts(request.user).get(pk=operation.pk)
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except AccountingException as e:
            logger.exception(
                "Accounting exception while creating crypto withdrawal"
            )
            raise InvalidException(
                target="amount",
                message=getattr(e, "reason", "Invalid withdrawal operation"),
            )


class CryptoWithdrawalConfirmationView(NonAtomicMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        key = request.GET.get('key')
        if not key:
            raise InvalidException('key', 'Key required')
        key = UUID(key)
        # OTT Should be backend
        user = deposit_confirmation_token_generator.validate(key)
        if user is None or user != request.user:
            raise InvalidException('key')
        operation = get_object_or_404(Operation, pk=pk,
                                      references__confirmation_token=key.hex)
        if not operation.status == OperationStatus.NEW:
            raise InvalidException('key', 'Withdrawal already confirmed')
        try:
            operation.hold()
        except AccountingException:
            operation.status = OperationStatus.CANCELLED
            operation.save()
            raise InvalidException('key', 'Operation conflict.')

        return Response()


class CryptoWithdrawalCalculateAPIView(APIView):
    def post(self, request, asset_id):
        asset = get_object_or_404(Asset.objects.all(), pk=asset_id)

        try:
            amount = request.data['amount']
        except (KeyError, TypeError):
            raise InvalidException(target='amount', message='Invalid amount')

        amount = sanitize_amount(
            amount,
            decimal_places=asset.decimals
        )
        fee = calculate_fee_crypto_withdrawal(amount, asset=asset)
        return Response({
            'data': {
                'amount': str(amount),
                'fee': str(fee.rounded),
                'total': str(amount - fee.rounded)
            }
        })


