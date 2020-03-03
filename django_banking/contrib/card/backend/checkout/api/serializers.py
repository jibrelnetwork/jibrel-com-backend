from rest_framework import serializers

from django_banking.contrib.card.backend.checkout.models import CheckoutCharge


class CheckoutTokenSerializer(serializers.Serializer):
    pass


class CheckoutPhoneSerializer(serializers.Serializer):
    country_code = serializers.CharField()
    number = serializers.CharField()


class CheckoutCardSerializer(serializers.Serializer):
    number = serializers.CharField(required=True)
    expiry_month = serializers.IntegerField(required=True)
    expiry_year = serializers.IntegerField(required=True)
    name = serializers.CharField()
    cvv = serializers.CharField(required=False)
    # billing_address = serializers.CharField()
    phone = CheckoutPhoneSerializer(many=False)


class CheckoutChargeSerializer(serializers.ModelSerializer):
    statusLatest = serializers.CharField(source='status_latest', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = CheckoutCharge
        fields = (
            'uuid',
            'statusLatest',
            'createdAt',
            'updatedAt',
        )
