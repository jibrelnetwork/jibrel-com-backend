from rest_framework import serializers

from django_banking.models import Operation
from jibrel.core.rest_framework import RegexValidator


class CheckoutTokenSerializer(serializers.Serializer):
    cardToken = serializers.CharField(
        required=True,
        validators=[RegexValidator(r'^(tok)_(\w{26})$')],
        error_messages={
            'invalid': 'Token is not valid',
        }
    )

    def validate_cardToken(self, value):
        value = value.strip()
        if Operation.objects.filter(references__checkout_token=value).exists():
            raise serializers.ValidationError('used', 'Token already used')
        return value
