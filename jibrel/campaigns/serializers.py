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

    class Meta:
        model = Security
        fields = (
            'uuid',
            'type',
            'created_at',
            'updated_at',
            'company'
        )


class OfferingSerializer(serializers.ModelSerializer):
    security = SecuritySerializer()
    equity = serializers.SerializerMethodField()

    class Meta:
        model = Offering
        fields = (
            'uuid',
            'security',
            'limit_min_amount',
            'limit_max_amount',
            'date_start',
            'date_end',
            'created_at',
            'updated_at',
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
