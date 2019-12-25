
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.fields import DecimalField

from django_banking import logger
from django_banking.api.helpers import sanitize_amount
from django_banking.api.serializers import DepositOperationSerializer
from django_banking.contrib.wire_transfer.api.validators.iban import IbanValidator
from django_banking.contrib.wire_transfer.api.validators.swift_code import swift_code_validator
from django_banking.contrib.wire_transfer.models import UserBankAccount, DepositWireTransferOperation, WithdrawalWireTransferOperation
from django_banking.core.api.fields import AssetPrecisionDecimal
from django_banking.limitations.enum import LimitType
from django_banking.limitations.exceptions import OutOfLimitsException
from django_banking.limitations.utils import validate_by_limits, get_user_limits
from django_banking.models.transactions.enum import OperationType


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
        model = UserBankAccount
        fields = ('id', 'swiftCode', 'bankName', 'holderName', 'ibanNumber')


class MaskedBankAccountSerializer(BaseBankAccountSerializer):
    id = serializers.UUIDField(source='uuid')
    ibanLastNumbers = serializers.SerializerMethodField('get_masked_iban')

    def get_masked_iban(self, obj):
        return obj.iban_number[-4:]

    class Meta:
        model = UserBankAccount
        fields = ('id', 'swiftCode', 'bankName', 'holderName', 'ibanLastNumbers')


class WireTransferDepositSerializer(serializers.ModelSerializer):
    amount = AssetPrecisionDecimal(source='*', real_source='total', asset_source='asset')

    class Meta:
        model = DepositWireTransferOperation

    def __init__(self, instance=None, bank_account=None, **kwargs):
        super().__init__(instance, **kwargs)
        self.user = self.context['request'].user
        try:
            bank_account = UserBankAccount.objects.get(pk=bank_account_id,
                                                       user=user,
                                                       is_active=True)
        except UserBankAccount.DoesNotExist:
            raise NotFound("Bank account with such id not found")
        ValidationError
        bank_account = self.context['request'].user


    def validate_amount(self, value):
        try:
            validate_by_limits(OperationType.DEPOSIT, bank_account.account.asset, value)
        except OutOfLimitsException as e:
            raise ValidationError(f'Amount should be greater than {e.bottom_limit}')

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


    def create(self, validated_data):
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
            logger.debug(
                "Bank account deposit operation %s created. User account %s, "
                "deposit bank account %s",
                operation, user_account, deposit_bank_account
            )

        except AccountingException:
            logger.exception(
                "Accounting exception on create bank account deposit operation"
            )
        raise APIException('Invalid deposit operation')

        amount = sanitize_amount(
            value,
            decimal_places=bank_account.account.asset.decimals
        )
        self


        from rest_framework.validators import UniqueForYearValidator

class WireTransferWithdrawalSerializer(DepositOperationSerializer):
    class Meta:
        model = WithdrawalWireTransferOperation


