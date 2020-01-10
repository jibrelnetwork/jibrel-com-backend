
from rest_framework import viewsets, mixins
from rest_framework.response import Response

from jibrel.wallets.models import Wallet
from jibrel.wallets.serializers import WalletSerializer


class WalletViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    """
    A viewset for manage Wallet instances.
    """
    serializer_class = WalletSerializer

    def get_object(self):
        wallet = Wallet.objects.get(user=self.request.user, uid=self.kwargs['pk'])
        return wallet

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request):
        queryset = Wallet.objects.filter(user=request.user)
        serializer = WalletSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        wallet = Wallet.objects.get(user=request.user, uid=pk)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

