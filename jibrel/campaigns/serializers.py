from django.conf import settings
from rest_framework import serializers

from jibrel.campaigns.models import (
    Company,
    Offering,
    Security
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            'name',
        )


class SecuritySerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')

    class Meta:
        model = Security
        fields = (
            'uuid',
            'type',
            'createdAt',
            'updatedAt',
            'company'
        )


class OfferingSerializer(serializers.ModelSerializer):
    security = SecuritySerializer()
    equity = serializers.SerializerMethodField()
    limitMinAmount = serializers.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2, source='limit_min_amount')
    limitMaxAmount = serializers.DecimalField(
        max_digits=settings.ACCOUNTING_MAX_DIGITS, decimal_places=2, source='limit_min_amount')
    dateStart = serializers.DateTimeField(source='date_start')
    dateEnd = serializers.DateTimeField(source='date_end')
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')

    class Meta:
        model = Offering
        fields = (
            'uuid',
            'security',
            'limitMinAmount',
            'limitMaxAmount',
            'dateStart',
            'dateEnd',
            'createdAt',
            'updatedAt',
            'valuation',
            'goal',
            'round',
            'shares',
            'price',
            'status',
            'equity'
        )

    def get_equity(self, obj):
        """Return as string
        """
        return '{0:f}'.format(obj.equity)
