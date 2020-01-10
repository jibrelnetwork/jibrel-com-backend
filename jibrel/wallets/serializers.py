from rest_framework import serializers

from jibrel.wallets.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        exclude = ['user', 'id']
        read_only_fields = ['version_number']

    def validate_uid(self, value):
        if self.instance and self.instance.uid != value:
            raise serializers.ValidationError("Can't change Wallet UID")
        return value

