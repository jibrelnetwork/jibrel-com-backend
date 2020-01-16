from rest_framework import serializers

from jibrel.core.rest_framework import AlwaysTrueFieldValidator
from jibrel.investment.models import InvestmentApplication


class InvestmentApplicationSerializer(serializers.ModelSerializer):
    isAgreedRisks = serializers.BooleanField(source='is_agreed_risks', validators=[AlwaysTrueFieldValidator()])
    isAgreedSubscription = serializers.BooleanField(
        source='is_agreed_subscription', validators=[AlwaysTrueFieldValidator()]
    )

    class Meta:
        model = InvestmentApplication
        fields = (
            'amount',
            'isAgreedRisks',
            'isAgreedSubscription',
        )
