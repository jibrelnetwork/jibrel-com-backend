import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django_banking.models import Operation


class CheckoutTokenSerializer(serializers.Serializer):
    cardToken = serializers.CharField(required=True)

    def validate_cardToken(self, value):
        value = value.strip()
        if not re.match('^(tok)_(\w{26})$', value):
            raise ValidationError('Bad token')
        elif Operation.objects.filter(references__checkout_token=value).exists():
            raise ValidationError('Token used')
        return value
