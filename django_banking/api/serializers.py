from decimal import Decimal
from typing import Dict

from rest_framework import serializers

from django_banking import logger
from django_banking.core.api.fields import AssetPrecisionDecimal
from django_banking.models import (
    Asset,
    Operation
)
from django_banking.models.transactions.enum import (
    OperationStatus,
    OperationType
)
from django_banking.models.transactions.models import (
    OperationConfirmationDocument
)


class AssetSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid')
    decimalPlaces = serializers.IntegerField(source='decimals')

    class Meta:
        model = Asset
        fields = ('id', 'name', 'symbol', 'type', 'decimalPlaces')


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
        if obj.type == OperationType.DEPOSIT:
            if obj.status == OperationStatus.HOLD:
                document_upload = self._get_confirmation_document(obj)
                if document_upload:
                    return 'processing'
            mapping = {
                OperationStatus.NEW: 'waiting_payment',
                OperationStatus.HOLD: 'waiting_payment',
                OperationStatus.COMMITTED: 'completed',
                OperationStatus.CANCELLED: 'cancelled',
                OperationStatus.DELETED: 'expired',
            }
        elif obj.type == OperationType.WITHDRAWAL:
            mapping = {
                OperationStatus.NEW: 'unconfirmed',
                OperationStatus.HOLD: 'processing',
                OperationStatus.COMMITTED: 'completed',
                OperationStatus.CANCELLED: 'cancelled',
                OperationStatus.DELETED: 'expired',
            }
        elif obj.type in {OperationType.BUY, OperationType.SELL}:
            mapping = {
                OperationStatus.NEW: 'processing',
                OperationStatus.HOLD: 'processing',
                OperationStatus.COMMITTED: 'completed',
                OperationStatus.CANCELLED: 'failed',
                OperationStatus.DELETED: 'failed',
            }

        try:
            return mapping[obj.status]
        except KeyError:
            logger.exception("Unhandled operation status %s (operation %s)",
                             obj.status, obj.uuid)
            return "undefined"

    def get_total_price(self, obj):
        total_price_data = obj.metadata.get('total_price', {})
        total_price = total_price_data.get('total')
        asset_id = total_price_data.get('quote_asset_id')
        if not total_price or not asset_id:
            return
        asset = Asset.objects.get(pk=asset_id)
        return str(Decimal(total_price).quantize(Decimal(10) ** -asset.decimals))

    def get_user_iban(self, obj):
        from django_banking.contrib.wire_transfer.models import UserBankAccount
        try:
            bank_account_uuid = obj.references['user_bank_account_uuid']
            return UserBankAccount.objects.get(pk=bank_account_uuid).iban_number[-4:]
        except (UserBankAccount.DoesNotExist, KeyError):
            return None


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
        from django_banking.contrib.wire_transfer.models import ColdBankAccount
        try:
            return ColdBankAccount.objects.get(
                account__transaction__operation=obj
            ).bank_account_details
        except ColdBankAccount.DoesNotExist:
            return None

    def get_deposit_reference_code(self, obj):
        return obj.references.get('reference_code')

    def get_crypto_deposit_address(self, obj):
        return obj.deposit_cryptocurrency_address and obj.deposit_cryptocurrency_address.address

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
        OperationType.DEPOSIT: DepositOperationSerializer(),
        OperationType.WITHDRAWAL: WithdrawalOperationSerializer(),
        OperationType.BUY: ExchangeOperationSerializer(),
        OperationType.SELL: ExchangeOperationSerializer(),
    }

    def to_representation(self, instance):
        return self.type_to_serializer[instance.type].to_representation(instance)


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
