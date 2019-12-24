from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ccwt import logger
from ccwt.api.helpers import sanitize_amount
from ccwt.api.serializers import OperationSerializer
from ccwt.contrib.crypto.models import CryptoAccount
from ccwt.models import UserAccount, Operation, Asset
from ccwt.models.accounts.exceptions import AccountingException
from ccwt.models.fee.utils import calculate_fee_crypto_withdrawal
from ccwt.models.transactions.enum import OperationStatus
from .serializers import CryptoAccountSerializer
from jibrel.core.errors import InvalidException


class CryptoAccountListAPIView(ListCreateAPIView):
    serializer_class = CryptoAccountSerializer

    def get_queryset(self):
        return CryptoAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
        )

    @permission_classes([IsAuthenticated, IsKYCVerifiedUser])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class CryptoAccountDetailsAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get_queryset(self):
        return CryptoAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CryptoAccountDepositAPIView(APIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get(self, request, asset_id):
        asset = get_object_or_404(Asset, pk=asset_id)

        deposit_account = DepositCryptoAccount.objects.for_customer(
            user=request.user, asset=asset
        )
        return Response({
            "address": deposit_account.address,
        })


class CryptoAccountWithdrawalAPIView(NonAtomicMixin, APIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

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
            token = deposit_confirmation_token_generator.generate(request.user)
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

            rendered = CryptoWithdrawalConfirmationEmailMessage.translate(request.user.profile.language).render({
                'name': request.user.profile.username,
                'amount': f'{amount} {crypto_account.account.asset.symbol}',
                'address': crypto_account.address,
                'withdrawal_confirmation_link': settings.APP_WITHDRAWAL_CONFIRM_LINK.format(
                    operation_id=operation.pk,
                    token=token.hex
                ),
            })
            send_mail.delay(
                task_context={'user_id': request.user.uuid.hex, 'user_ip_address': get_client_ip(request)},
                recipient=request.user.email,
                **rendered.serialize()
            )

            operation = PaymentOperation.objects.with_amounts(request.user).get(pk=operation.pk)
            serializer = OperationSerializer(operation)
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
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get(self, request, pk):
        key = request.GET.get('key')
        if not key:
            raise InvalidException('key', 'Key required')
        key = UUID(key)
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


