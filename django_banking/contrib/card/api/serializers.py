from rest_framework import serializers


class CardSerializer(serializers.Serializer):
    id = serializers.CharField()
    lastNumbers = serializers.CharField(source='last_four')
    holderName = serializers.CharField(source='name')
    type = serializers.CharField(source='brand')
    expMonth = serializers.IntegerField(source='exp_month')
    expYear = serializers.IntegerField(source='exp_year')
