import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class CheckoutTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        if not re.match('^(tok)_(\w{26})$', value):
            raise ValidationError('Bad token')
        return value
