from django.db import transaction
from rest_framework import serializers

from django_banking.api.serializers import AssetSerializer
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.rest_framework import AlwaysTrueFieldValidator
from jibrel.investment.models import (
    InvestmentApplication,
    InvestmentSubscription,
    PersonalAgreement
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


class CreateInvestmentApplicationSerializer(serializers.ModelSerializer):
    isAgreedRisks = serializers.BooleanField(source='is_agreed_risks', validators=[AlwaysTrueFieldValidator()])
    isAgreedSubscription = serializers.BooleanField(
        source='is_agreed_subscription', validators=[AlwaysTrueFieldValidator()]
    )

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        PersonalAgreement.objects.filter(
            offering=instance.offering,
            user=self.context['request'].user
        ).select_for_update().update(is_agreed=True)
        return instance

    class Meta:
        model = InvestmentApplication
        fields = (
            'amount',
            'isAgreedRisks',
            'isAgreedSubscription'
        )


class InvestmentApplicationSerializer(CreateInvestmentApplicationSerializer):
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')

    ownership = serializers.DecimalField(max_digits=9, decimal_places=6)
    offering = OfferingSerializer()
    asset = AssetSerializer()

    class Meta:
        model = InvestmentApplication
        fields = (
            'amount',
            'isAgreedRisks',
            'isAgreedSubscription',
            'status',
            'offering',
            'asset',
            'createdAt',
            'updatedAt',
            'ownership'
        )
