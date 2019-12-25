from rest_framework import serializers

from django_banking.contrib.wire_transfer.api.validators.iban import IbanValidator
from django_banking.contrib.wire_transfer.api.validators.swift_code import swift_code_validator
from django_banking.contrib.wire_transfer.models import BankAccount


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
