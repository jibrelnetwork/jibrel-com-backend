from django.db import transaction
from rest_framework import serializers

from django_banking.contrib.crypto.models import CryptoAccount
from django_banking.models import Account, Asset
from django_banking.models.accounts.enum import AccountType


class CryptoAccountSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='uuid', required=False)
    assetId = serializers.PrimaryKeyRelatedField(
        source="account.asset",
        queryset=Asset.objects.all()
    )

    class Meta:
        model = CryptoAccount
        fields = ('id', 'assetId', 'address')

    @transaction.atomic()
    def create(self, validated_data):
        asset = validated_data.pop('account')['asset']
        account = Account.objects.create(
            asset=asset, type=AccountType.TYPE_ACTIVE, strict=True
        )
        return CryptoAccount.objects.create(account=account, **validated_data)
