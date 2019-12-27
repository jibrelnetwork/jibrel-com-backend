
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.fields import DecimalField

from django_banking import logger
from django_banking.api.helpers import sanitize_amount
from django_banking.api.serializers import DepositOperationSerializer
from django_banking.contrib.wire_transfer.api.validators.iban import IbanValidator
from django_banking.contrib.wire_transfer.api.validators.swift_code import swift_code_validator
from django_banking.contrib.wire_transfer.models import UserBankAccount, DepositWireTransferOperation, \
    WithdrawalWireTransferOperation, ColdBankAccount
from django_banking.contrib.wire_transfer.signals import wire_transfer_deposit_requested
from django_banking.core.api.fields import AssetPrecisionDecimal
from django_banking.core.utils import get_client_ip
from django_banking.limitations.enum import LimitType
from django_banking.limitations.exceptions import OutOfLimitsException
from django_banking.limitations.utils import validate_by_limits
from django_banking.models import Operation, UserAccount
from django_banking.models.accounts.exceptions import AccountingException
from django_banking.models.transactions.enum import OperationType
from django_banking.utils import generate_deposit_reference_code


class ColdBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColdBankAccount
        fields = ('id', 'bank_account_details')


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
    coldBankAccount = ColdBankAccountSerializer(
        many=False,
        read_only=True
    )

    class Meta:
        fields = ['uuid', 'references', 'amount']
        model = DepositWireTransferOperation

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(instance, **kwargs)
        self.user = self.context['request'].user
        self.user_bank_account = self.context['user_bank_account']

    def set_references(self):
        reference_code = generate_deposit_reference_code()
        return {
            'user_bank_account_uuid': str(self.user_bank_account.uuid),
            'reference_code': reference_code
        }

    def get_coldBankAccount(self):
        try:
            cold_bank_account = ColdBankAccount.objects.for_customer(
                self.user
            )
        except ColdBankAccount.DoesNotExist:
            country_code = self.user.get_residency_country_code()
            # Return 500 in case we have no deposit bank account available
            logger.error("No active deposit bank account found for %s country",
                         country_code)
            raise Exception(f"No active deposit bank account found for {country_code}")
        return ColdBankAccountSerializer(instance=cold_bank_account)

    def validate_amount(self, value):
        try:
            validate_by_limits(OperationType.DEPOSIT, self.user_bank_account.account.asset, value)
        except OutOfLimitsException as e:
            raise ValidationError(f'Amount should be greater than {e.bottom_limit}')

        # TODO
        # check limit exceed and reject operation if it was

        return sanitize_amount(
            value,
            decimal_places=self.user_bank_account.account.asset.decimals
        )

    def create(self, validated_data):
        cold_bank_account = self.data.coldBankAccount
        references = self.data.references

        user_account = UserAccount.objects.for_customer(
            user=self.user,
            asset=cold_bank_account.account.asset
        )

        try:
            operation = self._meta.model.objects.create_deposit(
                payment_method_account=cold_bank_account.account,
                user_account=user_account,
                amount=validated_data['amount'],
                references=references
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
            raise APIException('Invalid deposit operation')

        wire_transfer_deposit_requested.send(
            sender=DepositWireTransferOperation,
            instance=operation,
            user_ip_address=get_client_ip(self.context['request'])
        )
        return operation


class WireTransferWithdrawalSerializer(DepositOperationSerializer):
    class Meta:
        model = WithdrawalWireTransferOperation


