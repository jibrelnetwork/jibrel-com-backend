from rest_framework import serializers

from django_banking.api.serializers import AssetSerializer
from django_banking.contrib.wire_transfer.api.serializers import (
    ColdBankAccountSerializer
)
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.rest_framework import AlwaysTrueFieldValidator
from jibrel.investment.models import (
    InvestmentApplication,
    InvestmentSubscription
)


class CreateInvestmentSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentSubscription
        fields = (
            'amount',
            'email'
        )


class InvestmentApplicationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', read_only=True)
    isAgreedRisks = serializers.BooleanField(source='is_agreed_risks', validators=[AlwaysTrueFieldValidator()])
    subscriptionAgreementStatus = serializers.CharField(source='subscription_agreement_status', read_only=True)
    subscriptionAgreementRedirectUrl = serializers.CharField(source='agreement.redirect_url', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    ownership = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    offering = OfferingSerializer(read_only=True)
    asset = AssetSerializer(read_only=True)
    bankAccount = ColdBankAccountSerializer(source='bank_account', read_only=True)
    depositReferenceCode = serializers.CharField(source='deposit_reference_code', read_only=True)

    class Meta:
        model = InvestmentApplication
        fields = (
            'id',
            'amount',
            'isAgreedRisks',
            'status',
            'offering',
            'asset',
            'ownership',
            'bankAccount',
            'depositReferenceCode',
            'subscriptionAgreementStatus',
            'subscriptionAgreementRedirectUrl',
            'createdAt',
            'updatedAt',
        )
        read_only_fields = (
            'status',
        )
