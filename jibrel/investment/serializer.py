from rest_framework import serializers
from rest_framework.fields import empty

from django_banking.api.serializers import AssetSerializer
from django_banking.contrib.wire_transfer.api.serializers import (
    ColdBankAccountSerializer
)
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.errors import ValidationError
from jibrel.core.rest_framework import AlwaysTrueFieldValidator
from jibrel.investment.models import (
    InvestmentApplication,
    InvestmentSubscription
)


class InvestmentSubscriptionSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    offering = OfferingSerializer(read_only=True)

    class Meta:
        model = InvestmentSubscription
        fields = (
            'amount',
            'email',
            'createdAt',
            'offering'
        )


class InvestmentApplicationSerializer(serializers.ModelSerializer):
    isAgreedRisks = serializers.BooleanField(source='is_agreed_risks', validators=[AlwaysTrueFieldValidator()])
    subscriptionAgreementStatus = serializers.CharField(source='subscription_agreement_status', read_only=True)
    subscriptionAgreementRedirectUrl = serializers.CharField(source='agreement.redirect_url', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    ownership = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    offering = OfferingSerializer(read_only=True)
    asset = AssetSerializer(read_only=True)
    depositReferenceCode = serializers.CharField(source='deposit_reference_code', read_only=True)
    bankAccount = ColdBankAccountSerializer(source='bank_account', read_only=True)

    class Meta:
        model = InvestmentApplication
        fields = (
            'uuid',
            'amount',
            'isAgreedRisks',
            'status',
            'offering',
            'asset',
            'ownership',
            'depositReferenceCode',
            'bankAccount',
            'subscriptionAgreementStatus',
            'subscriptionAgreementRedirectUrl',
            'createdAt',
            'updatedAt',
        )
        read_only_fields = (
            'uuid',
            'status',
        )

    def __init__(self, instance=None, data=empty, **kwargs):
        self.offering = kwargs.pop('offering', None)
        if self.offering is None and instance is None:
            raise TypeError('offering argument is required while creating')
        super().__init__(instance, data, **kwargs)

    def validate_amount(self, amount):
        offering = self.offering or self.instance.offering
        if amount < offering.limit_min_amount:
            raise ValidationError(f'Amount must not be lower than {offering.limit_min_amount}')
        if amount > offering.limit_allowed_amount:
            raise ValidationError(f'Amount must not be higher than {offering.limit_allowed_amount}')
        return amount


class DepositWireTransferInvestmentApplicationSerializer(serializers.ModelSerializer):
    bankAccount = ColdBankAccountSerializer(source='bank_account', read_only=True)

    class Meta:
        model = InvestmentApplication
        fields = (
            'bankAccount',
        )


class DepositCardInvestmentApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentApplication
        fields = (
            'deposit',
        )
        read_only_fields = (
            'deposit',
        )
