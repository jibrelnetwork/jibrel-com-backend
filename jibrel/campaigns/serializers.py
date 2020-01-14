from rest_framework import serializers

from jibrel.campaigns.models import Security, Offering


class CMSSecuritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Security
        fields = (
            'uuid',
            'type',
            'created_at',
            'updated_at',
        )


class CMSOfferingSerializer(serializers.ModelSerializer):
    security = CMSSecuritySerializer()

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
        )
