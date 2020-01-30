from django.db import transaction
from rest_framework import serializers

from django_banking.api.serializers import AssetSerializer
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.errors import ValidationError
from jibrel.core.rest_framework import AlwaysTrueFieldValidator
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement
)


class CreateInvestmentApplicationSerializer(serializers.ModelSerializer):
    isAgreedRisks = serializers.BooleanField(source='is_agreed_risks', validators=[AlwaysTrueFieldValidator()])
    isAgreedSubscription = serializers.BooleanField(
        source='is_agreed_subscription', validators=[AlwaysTrueFieldValidator()]
    )
    isAgreedPersonalAgreement = serializers.NullBooleanField(source='is_agreed_personal_agreement')

    def __init__(self, offering, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.offering = offering

    def validate_isAgreedPersonalAgreement(self, value):
        qs = PersonalAgreement.objects.filter(
            offering=self.offering,
            user=self.context['request'].user
        )
        if qs.exists() and value is not True:
            raise ValidationError('You must agree your personal agreements')
        return value

    @transaction.atomic
    def create(self, validated_data):
        validated_data['offering'] = self.offering
        validated_data.pop('is_agreed_personal_agreement')
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
            'isAgreedSubscription',
            'isAgreedPersonalAgreement'
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
            'isAgreedPersonalAgreement',
            'status',
            'offering',
            'asset',
            'createdAt',
            'updatedAt',
            'ownership'
        )
