import decimal
import logging
from decimal import Decimal
from typing import Dict

from django.db import transaction
from rest_framework import serializers

from jibrel.accounting.models import Account, Asset, Operation
from jibrel.accounting.serializers import AssetPrecisionDecimal
from jibrel.assets.models import AssetPair
from jibrel.exchanges.repositories.price import (
    PriceNotFoundException,
    price_repository
)
from jibrel.payments.models import (
    DepositBankAccount,
    OperationConfirmationDocument
)

from .iban import IbanValidator
from .models import BankAccount, CryptoAccount, DepositCryptoAccount
from .swift_code import swift_code_validator

logger = logging.getLogger(__name__)


class AssetSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid')
    decimalPlaces = serializers.IntegerField(source='decimals')

    class Meta:
        model = Asset
        fields = ('id', 'name', 'symbol', 'type', 'decimalPlaces')


class AccountBalanceSerializer(serializers.Serializer):
    """Account balance serializer.

    Serialize Account records for `/v1/balance/` endpoint.

    `balance` should be annotated on instances (use `with_balances()` queryset method)
    before serialization.
    """

    accountId = serializers.UUIDField(source='uuid')
    assetId = serializers.UUIDField(source='asset.uuid')
    balance = AssetPrecisionDecimal(source='*', real_source='balance', asset_source='asset')
    totalPrice = serializers.SerializerMethodField('get_total_price')

    def get_total_price(self, obj):
        base_asset = obj.asset
        quote_asset = self.context['quote_asset']
        if quote_asset == base_asset:
            return str(obj.balance)
        try:
            pair_id = AssetPair.objects.get(base=base_asset, quote=quote_asset)
            price = price_repository.get_by_pair_id(pair_id.uuid)
            return str(
                (obj.balance * price.sell).quantize(
                    Decimal('.1') ** quote_asset.decimals, rounding=decimal.ROUND_UP
                )
            )
        except (PriceNotFoundException, AssetPair.DoesNotExist):
            return None


class BaseBankAccountSerializer(serializers.ModelSerializer):
    swiftCode = serializers.CharField(source='swift_code', max_length=11,
                                      validators=[swift_code_validator])
    bankName = serializers.CharField(source='bank_name', max_length=200)
    holderName = serializers.CharField(source='holder_name', max_length=200)


class BankAccountSerializer(BaseBankAccountSerializer):
    id = serializers.UUIDField(source='uuid', required=False)
    ibanNumber = serializers.CharField(source='iban_number', max_length=34,
                                       validators=[IbanValidator()])

    class Meta:
        model = BankAccount
        fields = ('id', 'swiftCode', 'bankName', 'holderName', 'ibanNumber')


class MaskedBankAccountSerializer(BaseBankAccountSerializer):
    id = serializers.UUIDField(source='uuid')
    ibanLastNumbers = serializers.SerializerMethodField('get_masked_iban')

    def get_masked_iban(self, obj):
        return obj.iban_number[-4:]

    class Meta:
        model = BankAccount
        fields = ('id', 'swiftCode', 'bankName', 'holderName', 'ibanLastNumbers')


class BaseOperationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid')
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    feeAmount = serializers.CharField(source='fee_amount')
    feeAsset = serializers.CharField(source='fee_asset')
    feeAssetId = serializers.CharField(source='fee_asset_id')
    status = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = (
            'id',
            'createdAt',
            'updatedAt',
            'type',
            'debitAmount',
            'debitAsset',
            'debitAssetId',
            'creditAmount',
            'creditAsset',
            'creditAssetId',
            'feeAmount',
            'feeAsset',
            'feeAssetId',
            'status',
            'confirmationDocument',
            'depositBankAccount',
            'depositReferenceCode',
            'cryptoDepositAddress',
            'userIban',
        )

    def _get_confirmation_document(self, obj):
        return OperationConfirmationDocument.objects.filter(
            operation=obj
        ).order_by('-created_at').first()

    def get_status(self, obj: Operation):
        mapping: Dict[str, str] = {}
        if obj.type == Operation.DEPOSIT:
            if obj.status == Operation.HOLD:
                document_upload = self._get_confirmation_document(obj)
                if document_upload:
                    return 'processing'
            mapping = {
                Operation.NEW: 'waiting_payment',
                Operation.HOLD: 'waiting_payment',
                Operation.COMMITTED: 'completed',
                Operation.CANCELLED: 'cancelled',
                Operation.DELETED: 'expired',
            }
        elif obj.type == Operation.WITHDRAWAL:
            mapping = {
                Operation.NEW: 'unconfirmed',
                Operation.HOLD: 'processing',
                Operation.COMMITTED: 'completed',
                Operation.CANCELLED: 'cancelled',
                Operation.DELETED: 'expired',
            }
        elif obj.type in {Operation.BUY, Operation.SELL}:
            mapping = {
                Operation.NEW: 'processing',
                Operation.HOLD: 'processing',
                Operation.COMMITTED: 'completed',
                Operation.CANCELLED: 'failed',
                Operation.DELETED: 'failed',
            }

        try:
            return mapping[obj.status]
        except KeyError:
            logger.exception("Unhandled operation status %s (operation %s)",
                             obj.status, obj.uuid)
            return "undefined"


class DepositOperationSerializer(BaseOperationSerializer):
    debitAmount = serializers.CharField(source='debit_amount')
    debitAsset = serializers.CharField(source='debit_asset')
    debitAssetId = serializers.CharField(source='debit_asset_id')
    confirmationDocument = serializers.SerializerMethodField(
        method_name='get_confirmation_document'
    )
    depositBankAccount = serializers.SerializerMethodField(
        method_name='get_deposit_bank_account'
    )
    depositReferenceCode = serializers.SerializerMethodField(
        method_name='get_deposit_reference_code'
    )
    cryptoDepositAddress = serializers.SerializerMethodField(
        method_name='get_crypto_deposit_address'
    )
    userIban = serializers.SerializerMethodField(
        method_name='get_user_iban'
    )
    totalPrice = serializers.SerializerMethodField(
        method_name='get_total_price'
    )
    txHash = serializers.SerializerMethodField(
        method_name='get_tx_hash'
    )

    class Meta:
        model = Operation
        fields = (
            'id',
            'createdAt',
            'updatedAt',
            'type',
            'debitAmount',
            'debitAsset',
            'debitAssetId',
            'feeAmount',
            'feeAsset',
            'feeAssetId',
            'status',
            'confirmationDocument',
            'depositBankAccount',
            'depositReferenceCode',
            'cryptoDepositAddress',
            'userIban',
            'totalPrice',
            'txHash'
        )

    def get_confirmation_document(self, obj):
        doc = self._get_confirmation_document(obj)
        if doc:
            return doc.file.url
        else:
            return None

    def get_deposit_bank_account(self, obj):
        try:
            return DepositBankAccount.objects.get(
                account__transaction__operation=obj
            ).bank_account_details
        except DepositBankAccount.DoesNotExist:
            return None

    def get_deposit_reference_code(self, obj):
        return obj.references.get('reference_code')

    def get_crypto_deposit_address(self, obj):
        try:
            return DepositCryptoAccount.objects.get(account__transaction__operation=obj).address
        except DepositCryptoAccount.DoesNotExist:
            return None

    def get_user_iban(self, obj):
        try:
            bank_account_uuid = obj.references['user_bank_account_uuid']
            return BankAccount.objects.get(pk=bank_account_uuid).iban_number[-4:]
        except (BankAccount.DoesNotExist, KeyError):
            return None

    def get_total_price(self, obj):
        total_price_data = obj.metadata.get('total_price', {})
        total_price = total_price_data.get('total')
        asset_id = total_price_data.get('quote_asset_id')
        if not total_price or not asset_id:
            return
        asset = Asset.objects.get(pk=asset_id)
        return str(Decimal(total_price).quantize(Decimal(10) ** -asset.decimals))

    def get_tx_hash(self, obj):
        return obj.metadata.get('tx_hash')


class WithdrawalOperationSerializer(BaseOperationSerializer):
    creditAmount = serializers.CharField(source='credit_amount')
    creditAsset = serializers.CharField(source='credit_asset')
    creditAssetId = serializers.CharField(source='credit_asset_id')
    totalPrice = serializers.SerializerMethodField(
        method_name='get_total_price'
    )
    userIban = serializers.SerializerMethodField(
        method_name='get_user_iban'
    )

    class Meta:
        model = Operation
        fields = (
            'id',
            'createdAt',
            'updatedAt',
            'type',
            'creditAmount',
            'creditAsset',
            'creditAssetId',
            'feeAmount',
            'feeAsset',
            'feeAssetId',
            'status',
            'totalPrice',
            'userIban',
        )

    def get_total_price(self, obj):
        total_price_data = obj.metadata.get('total_price', {})
        total_price = total_price_data.get('total')
        asset_id = total_price_data.get('quote_asset_id')
        if not total_price or not asset_id:
            return
        asset = Asset.objects.get(pk=asset_id)
        return str(Decimal(total_price).quantize(Decimal(10) ** -asset.decimals))

    def get_user_iban(self, obj):
        try:
            bank_account_uuid = obj.references['user_bank_account_uuid']
            return BankAccount.objects.get(pk=bank_account_uuid).iban_number[-4:]
        except (BankAccount.DoesNotExist, KeyError):
            return None


class ExchangeOperationSerializer(BaseOperationSerializer):
    debitAmount = serializers.CharField(source='debit_amount')
    debitAsset = serializers.CharField(source='debit_asset')
    debitAssetId = serializers.CharField(source='debit_asset_id')
    creditAmount = serializers.CharField(source='credit_amount')
    creditAsset = serializers.CharField(source='credit_asset')
    creditAssetId = serializers.CharField(source='credit_asset_id')
    exchangeRate = serializers.SerializerMethodField(
        method_name='get_exchange_rate',
    )

    class Meta:
        model = Operation
        fields = (
            'id',
            'createdAt',
            'updatedAt',
            'type',
            'debitAmount',
            'debitAsset',
            'debitAssetId',
            'creditAmount',
            'creditAsset',
            'creditAssetId',
            'feeAmount',
            'feeAsset',
            'feeAssetId',
            'status',
            'exchangeRate',
        )

    def get_exchange_rate(self, obj):
        return obj.metadata.get('exchange_rate')


class OperationSerializer(serializers.Serializer):
    type_to_serializer = {
        Operation.DEPOSIT: DepositOperationSerializer(),
        Operation.WITHDRAWAL: WithdrawalOperationSerializer(),
        Operation.BUY: ExchangeOperationSerializer(),
        Operation.SELL: ExchangeOperationSerializer(),
    }

    def to_representation(self, instance):
        return self.type_to_serializer[instance.type].to_representation(instance)


class CryptoAccountSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', required=False)
    assetId = serializers.PrimaryKeyRelatedField(
        source="account.asset",
        queryset=Asset.objects.all()
    )

    class Meta:
        model = CryptoAccount
        fields = ('id', 'assetId', 'address')

    def create(self, validated_data):
        asset = validated_data.pop('account')['asset']
        with transaction.atomic():
            account = Account.objects.create(
                asset=asset, type=Account.TYPE_ACTIVE, strict=True
            )
            return CryptoAccount.objects.create(account=account, **validated_data)


class UploadConfirmationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationConfirmationDocument
        fields = ('file',)


class LimitsSerializer(serializers.Serializer):
    asset = serializers.UUIDField(source='asset.uuid')
    total = AssetPrecisionDecimal(source='*', real_source='total', asset_source='asset')
    available = AssetPrecisionDecimal(source='*', real_source='available', asset_source='asset')
    interval = serializers.CharField(source='interval.value')
    type = serializers.CharField(source='type.value')
    resetAt = serializers.DateTimeField(source='reset_date')


class CardSerializer(serializers.Serializer):
    id = serializers.CharField()
    lastNumbers = serializers.CharField(source='last_four')
    holderName = serializers.CharField(source='name')
    type = serializers.CharField(source='brand')
    expMonth = serializers.IntegerField(source='exp_month')
    expYear = serializers.IntegerField(source='exp_year')
