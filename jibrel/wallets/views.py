
from rest_framework import (
    mixins,
    viewsets
)

from jibrel.wallets.models import Wallet
from jibrel.wallets.serializers import (
    WalletSerializer,
    WalletUpdateSerializer,
)


class WalletViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    A viewset for manage Wallet instances.
    """
    # serializer_class = WalletSerializer

    # lookup_field = 'uid'

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'create'):
            return WalletSerializer
        if self.action in ('update', 'partial_update'):
            return WalletUpdateSerializer

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
