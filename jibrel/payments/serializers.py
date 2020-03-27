from rest_framework import serializers

from django_banking.api.serializers import (
    DepositOperationSerializer,
    ExchangeOperationSerializer,
    OperationSerializer,
    RefundOperationSerializer,
    WithdrawalOperationSerializer
)
from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationType


class InvestmentDepositOperationSerializer(DepositOperationSerializer):
    investmentApplication = serializers.SerializerMethodField(
        method_name='get_investment_application'
    )

    def get_investment_application(self, obj):
        investment_application = obj.deposited_application.first()
        if investment_application:
            return str(investment_application.pk)

    class Meta:
        model = Operation
        fields = list(DepositOperationSerializer.Meta.fields) + [
            'investmentApplication'
        ]


class InvestmentOperationSerializer(OperationSerializer):
    type_to_serializer = {
        OperationType.DEPOSIT: InvestmentDepositOperationSerializer(),
        OperationType.WITHDRAWAL: WithdrawalOperationSerializer(),
        OperationType.BUY: ExchangeOperationSerializer(),
        OperationType.SELL: ExchangeOperationSerializer(),
        OperationType.REFUND: RefundOperationSerializer(),
    }

    def to_representation(self, instance):
        return self.type_to_serializer[instance.type].to_representation(instance)


class FoloosiChargeSerializer(serializers.Serializer):
    chargeId = serializers.CharField(source='charge_id')

    class Meta:
        model = Operation
        fields = (
            'chargeId',
        )
