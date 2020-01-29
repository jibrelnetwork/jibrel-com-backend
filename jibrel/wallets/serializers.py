from rest_framework import serializers

from jibrel.wallets.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        exclude = ['user', 'address', 'deleted']
        read_only_fields = ['version_number']


class WalletUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['name']
