import logging
from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    get_object_or_404
)
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from jibrel.accounting.exceptions import AccountingException
from jibrel.accounting.models import Account, Asset, Operation
from jibrel.assets.models import AssetPair
from jibrel.core.exceptions import NonSupportedCountryException
from jibrel.core.utils import get_client_ip
from jibrel.exchanges.repositories.price import price_repository
from jibrel.payments.fees import (
    calculate_fee_bank_account_withdrawal,
    calculate_fee_crypto_withdrawal
)
from jibrel.payments.limits import (
    LimitType,
    OutOfLimitsException,
    get_user_limits,
    validate_by_limits
)
from jibrel.payments.permissions import IsCardOwner
from jibrel.payments.tap.base import (
    ChargeStatus,
    InvalidCardId,
    InvalidChargeId,
    InvalidCustomer,
    TapClientException,
    get_tap_client
)
from jibrel.payments.utils import generate_deposit_reference_code

from ..authentication.token_generator import (
    deposit_confirmation_token_generator
)
from ..core.errors import ValidationError, InvalidException
from ..core.permissions import IsKYCVerifiedUser
from ..notifications.email import (
    CryptoWithdrawalConfirmationEmailMessage,
    FiatDepositRequestedEmailMessage,
    LocalFiatWithdrawalRequestedEmailMessage
)
from ..notifications.tasks import send_mail
from .models import (
    BankAccount,
    CryptoAccount,
    DepositBankAccount,
    DepositCryptoAccount,
    FeeUserAccount,
    PaymentOperation,
    RoundingUserAccount,
    UserAccount
)
from .serializers import (
    AccountBalanceSerializer,
    AssetSerializer,
    BankAccountSerializer,
    CardSerializer,
    CryptoAccountSerializer,
    LimitsSerializer,
    MaskedBankAccountSerializer,
    OperationSerializer,
    UploadConfirmationRequestSerializer
)
from .tap import (
    create_charge_operation,
    get_or_create_tap_customer_id,
    process_tap_charge
)

logger = logging.getLogger(__name__)


class CustomCursorPagination(CursorPagination):
    ordering = '-created_at'
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'data': data,
        })


class NonAtomicMixin:
    @transaction.non_atomic_requests
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def sanitize_amount(value, decimal_places=None):
    try:
        amount = Decimal(value)

        if decimal_places:
            decimal_exp = Decimal('10') ** -decimal_places
            if amount.quantize(decimal_exp) != amount:
                raise InvalidException(target='amount',
                                       message='Value precision error')
    except (InvalidOperation, TypeError):
        raise InvalidException(target='amount',
                               message='Invalid amount value')

    if amount <= 0:
        raise InvalidException(target='amount',
                               message='Amount must be greater than 0')

    return amount


class AssetsListAPIView(ListAPIView):
    serializer_class = AssetSerializer

    def get_queryset(self):
        qs = Asset.objects.all()
        if 'country' in self.request.GET:
            qs = qs.filter(country=self.request.GET['country'].upper())
        return qs


class BalanceAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    serializer_class = AccountBalanceSerializer

    def get_queryset(self):
        return UserAccount.objects.get_user_accounts(self.request.user)

    def get_serializer_context(self):
        quote_asset = None
        quote_asset_uuid = self.request.GET.get('quote')

        if quote_asset_uuid:
            try:
                quote_asset_uuid = UUID(quote_asset_uuid)
            except (AttributeError, ValueError):
                raise ValidationError(target='quote',
                                      message="Invalid asset id")

            try:
                quote_asset = Asset.objects.get(pk=quote_asset_uuid)
            except Asset.DoesNotExist:
                raise ValidationError(target='quote',
                                      message="Quote asset doesn't exist")
            logger.debug("Show balances using %s currency rates", quote_asset)

        if quote_asset is None:
            country_code = self.request.user.get_residency_country_code()
            quote_asset = Asset.objects.get(country=country_code)
            logger.debug(
                "Show balances using default user currency %s (%s country)",
                quote_asset, country_code
            )

        return {
            'quote_asset': quote_asset
        }


class OperationViewSet(ReadOnlyModelViewSet):
    serializer_class = OperationSerializer

    pagination_class = CustomCursorPagination
    page_size_query_param = 'cursor'  # TODO: WTF? Why `cursor`?

    def get_queryset(self):
        try:
            qs = PaymentOperation.objects.with_amounts(
                self.request.user
            ).for_user(
                self.request.user,
                only_allowed_assets=False
            ).order_by('-created_at')
        except NonSupportedCountryException:
            qs = PaymentOperation.objects.none()
        return qs

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if not response.exception:
            response.data = {
                'data': response.data
            }
        return response


class UploadOperationConfirmationAPIView(APIView):

    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def post(self, request, pk):
        user_accounts = UserAccount.objects.get_user_accounts(request.user)
        operation = get_object_or_404(
            Operation, transactions__account__in=user_accounts, pk=pk
        )
        serializer = UploadConfirmationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(operation=operation)
        return Response(status=status.HTTP_201_CREATED)


class BankAccountListAPIView(ListCreateAPIView):

    """User bank accounts list.
    """

    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user, is_active=True)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BankAccountSerializer
        return MaskedBankAccountSerializer

    def perform_create(self, serializer):
        country_code = self.request.user.get_residency_country_code()
        with transaction.atomic():
            asset = Asset.objects.get(country=country_code)
            account = Account.objects.create(
                asset=asset, type=Account.TYPE_NORMAL, strict=False
            )
            serializer.save(user=self.request.user, account=account)


class BankAccountDetailsAPIView(DestroyAPIView):

    """Delete bank account.
    """

    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    lookup_url_kwarg = 'bank_account_id'

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class BankAccountDepositAPIView(NonAtomicMixin, APIView):

    """Create bank account deposit request.
    """

    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def post(self, request, bank_account_id):  # noqa
        try:
            bank_account = BankAccount.objects.get(pk=bank_account_id,
                                                   user=request.user,
                                                   is_active=True)
        except BankAccount.DoesNotExist:
            raise NotFound("Bank account with such id not found")

        try:
            amount = request.data['amount']
        except (KeyError, TypeError):
            raise InvalidException(target='amount', message='Invalid amount')

        amount = sanitize_amount(
            amount,
            decimal_places=bank_account.account.asset.decimals
        )

        try:
            validate_by_limits(Operation.DEPOSIT, bank_account.account.asset, amount)
        except OutOfLimitsException as e:
            raise InvalidException(target='amount', message=f'Amount should be greater than {e.bottom_limit}')

        try:
            deposit_bank_account = DepositBankAccount.objects.for_customer(
                request.user
            )
        except DepositBankAccount.DoesNotExist:
            # Return 500 in case we have no deposit bank account available
            logger.error("No active deposit bank account found for %s country",
                         request.user.get_residency_country_code())
            raise Exception("No active deposit bank account found for %s" % \
                            request.user.get_residency_country_code())

        user_account = UserAccount.objects.for_customer(
            user=request.user, asset=deposit_bank_account.account.asset
        )

        reference_code = generate_deposit_reference_code()

        try:
            operation = Operation.objects.create_deposit(
                payment_method_account=deposit_bank_account.account,
                user_account=user_account,
                amount=amount,
                references={
                    'user_bank_account_uuid': str(bank_account.uuid),
                    'reference_code': reference_code
                }
            )
            logger.info(
                "Bank account deposit operation %s created. User account %s, "
                "deposit bank account %s",
                operation, user_account, deposit_bank_account
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
        rendered = FiatDepositRequestedEmailMessage.translate(request.user.profile.language).render({
            'name': request.user.profile.username,
            'amount': f'{amount} {user_account.asset.symbol}',
        })
        send_mail.delay(
            recipient=request.user.email,
            task_context={'user_id': request.user.uuid.hex, 'user_ip_address': get_client_ip(request)},
            **rendered.serialize(),
        )
        return Response(
            {
                'id': str(operation.uuid),
                'depositBankAccount': deposit_bank_account.bank_account_details,
                'depositReferenceCode': reference_code
            },
            status=status.HTTP_201_CREATED
        )


class BankAccountWithdrawalAPIView(NonAtomicMixin, APIView):

    """Create bank account withdrawal request.
    """

    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def post(self, request, bank_account_id):
        bank_account = get_object_or_404(
            BankAccount.objects.filter(is_active=True, user=request.user)
                               .select_related('account'),
            pk=bank_account_id
        )

        try:
            amount = request.data['amount']
        except (KeyError, TypeError):
            raise InvalidException(target='amount', message='Invalid amount')

        amount = sanitize_amount(
            amount,
            decimal_places=bank_account.account.asset.decimals
        )

        try:
            validate_by_limits(Operation.DEPOSIT, bank_account.account.asset, amount)
        except OutOfLimitsException as e:
            raise InvalidException(target='amount', message=f'Amount should be greater than {e.bottom_limit}')

        withdrawal_account = bank_account.account

        user_account = UserAccount.objects.for_customer(
            user=request.user, asset=withdrawal_account.asset
        )

        fee_account = FeeUserAccount.objects.for_customer(
            user=request.user, asset=withdrawal_account.asset
        )
        fee = calculate_fee_bank_account_withdrawal(amount=amount, asset=withdrawal_account.asset)
        fee_amount = fee.rounded
        rounding_account = RoundingUserAccount.objects.for_customer(request.user, fee_account.asset)
        amount -= fee_amount
        if amount <= 0:
            raise InvalidException(
                target="amount",
                message="Must be greater than 0",
            )
        try:
            operation = Operation.objects.create_withdrawal(
                user_account=user_account,
                payment_method_account=withdrawal_account,
                fee_account=fee_account,
                fee_amount=fee_amount,
                amount=amount,
                rounding_account=rounding_account,
                rounding_amount=fee.remainder,
                references={
                    'user_bank_account_uuid': str(bank_account.uuid),
                }
            )
        except AccountingException as e:
            logger.exception(
                "Accounting exception on create bank account withdrawal"
            )
            raise InvalidException(
                target="amount",
                message=getattr(e, "reason", "Invalid withdrawal operation"),
            )

        # check limit exceed and reject operation if it was
        user_limits = get_user_limits(request.user)
        logger.debug("Available user limits: %s", user_limits)
        for limit in user_limits:
            if limit.type == LimitType.WITHDRAWAL and limit.available < 0:
                operation.reject("Withdrawal limit exceed")
                raise InvalidException(
                    target="amount",
                    message="Withdrawal limit exceed"
                )

        operation = PaymentOperation.objects.with_amounts(request.user).get(
            pk=operation.pk
        )
        serializer = OperationSerializer(operation)
        rendered = LocalFiatWithdrawalRequestedEmailMessage.translate(request.user.profile.language).render({
            'name': request.user.profile.username,
            'amount': f'{amount} {bank_account.account.asset.symbol}',
        })
        send_mail.delay(
            recipient=request.user.email,
            task_context={'user_id': request.user.uuid.hex, 'user_ip_address': get_client_ip(request)},
            **rendered.serialize(),
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        if not operation.status == Operation.NEW:
            raise InvalidException('key', 'Withdrawal already confirmed')
        try:
            operation.hold()
        except AccountingException:
            operation.status = Operation.CANCELLED
            operation.save()
            raise InvalidException('key', 'Operation conflict.')

        return Response()


class PaymentLimitsListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]

    def get(self, request):
        serializer = LimitsSerializer(get_user_limits(request.user), many=True)
        return Response({
            'data': serializer.data
        })


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


class BankAccountWithdrawalCalculateAPIView(APIView):
    def post(self, request, bank_account_id):
        bank_account = get_object_or_404(BankAccount.objects.all(), pk=bank_account_id)
        asset = bank_account.account.asset

        try:
            amount = request.data['amount']
        except (KeyError, TypeError):
            raise InvalidException(target='amount', message='Invalid amount')

        amount = sanitize_amount(
            amount,
            decimal_places=asset.decimals
        )
        fee = calculate_fee_bank_account_withdrawal(amount, asset=asset)
        return Response({
            'data': {
                'amount': str(amount),
                'fee': str(fee.rounded),
                'total': str(amount - fee.rounded)
            }
        })


class CardListAPIView(APIView):

    """List saved plastic cards saved by authenticated user.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser)

    def get(self, request):
        customer_id = get_or_create_tap_customer_id(request.user)

        # TODO: cache
        with get_tap_client() as tap_client:
            try:
                cards = tap_client.get_card_list(customer_id)
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('card_id', 'Invalid customer')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Payment gateway error')

        return Response({
            "data": {
                "customerId": customer_id,
                "cards": CardSerializer(cards, many=True).data
            }
        })


class CardDepositAPIView(APIView):

    """Start TAP deposit routine.

    Create charge on tap side, and return redirect url for user (in case of
    3d secure) or transaction id if already charged.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser, IsCardOwner)

    def post(self, request, card_id):
        self.check_object_permissions(request, card_id)

        amount = sanitize_amount(request.data['amount'])
        asset = Asset.objects.main_fiat_for_customer(request.user)
        customer_id = request.user.profile.tap_customer_id

        operation = create_charge_operation(request.user, asset, card_id,
                                            amount, hold=False)

        redirect_url = settings.APP_OPERATION_LINK.format(operation_id=operation.uuid)

        with get_tap_client() as tap_client:
            try:
                card = tap_client.get_card(customer_id, card_id)
                charge = tap_client.create_charge(
                    customer_id=customer_id,
                    amount=amount,
                    currency=asset,
                    redirect_url=redirect_url,
                    card_id=card_id
                )
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('card_id', 'Invalid customer')
            except InvalidCardId:
                logger.error("Invalid card id %s for customer %s (user %s)",
                             card_id, customer_id, request.user)
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Invalid card id')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('card_id', 'Payment gateway error')

        operation = process_tap_charge(request.user, charge, card)

        if charge.status == ChargeStatus.INITIATED and charge.transaction.url:
            return Response({
                'data': {
                    'redirect_url': charge.transaction.url
                }
            })
        elif charge.status == ChargeStatus.CAPTURED:
            return Response({
                'data': {
                    'operationId': operation.uuid
                }
            })
        else:
            raise ValidationError("amount", "Card payment exception")


class CardChargeAPIView(APIView):

    """Get operation id for tap charge id.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsKYCVerifiedUser, IsCardOwner)

    def post(self, request, card_id):
        self.check_object_permissions(request, card_id)

        charge_id = request.data.get('charge_id')
        if not charge_id:
            raise InvalidException('charge_id', 'Required field', 'required')

        with get_tap_client() as tap_client:
            try:
                charge = tap_client.get_charge(charge_id)
            except InvalidChargeId:
                raise InvalidException('charge_id', 'Invalid charge id',
                                       'invalid')

            # TODO: handle errors
            try:
                card = tap_client.get_card(
                    request.user.profile.tap_customer_id,
                    card_id
                )
            except InvalidCustomer:
                logger.error("Invalid customer id saved in db for user %s",
                             request.user)
                raise InvalidException('charge_id', 'Invalid customer')
            except InvalidCardId:
                logger.error("Invalid card id %s for customer %s (user %s)",
                             card_id, charge.customer, request.user)
                # TODO: specific exception/code?
                raise InvalidException('charge_id', 'Invalid card id')
            except TapClientException:
                logger.exception("Unpredicted TAP error")
                # TODO: specific exception/code?
                raise InvalidException('charge_id', 'Payment gateway error')

        operation = process_tap_charge(request.user, charge, card)

        return Response({
            'data': {
                'operationId': str(operation.uuid)
            }
        })
