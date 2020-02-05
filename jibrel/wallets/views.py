
from rest_framework import (
    mixins,
    viewsets
)
from rest_framework.decorators import action
from rest_framework.response import Response

from jibrel.wallets.models import (
    Wallet,
    get_addresses_names
)
from jibrel.wallets.serializers import (
    WalletSerializer,
    WalletUpdateSerializer
)

SEARCH_QUERY_MIN_LEN = 3


class WalletViewSet(mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    A viewset for manage Wallet instances.
    """

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'create'):
            return WalletSerializer
        if self.action in ('update', 'partial_update'):
            return WalletUpdateSerializer

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user, deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q')
        if not q or len(q) < SEARCH_QUERY_MIN_LEN:
           data = []
        else:
            data = Wallet.search(q)
        return Response(data)

    @action(detail=False, methods=['get'])
    def get_names(self, request):
        address_list = [a.strip().lower() for a in request.query_params.get('addresses', '').split(',')]
        result = get_addresses_names(address_list)
        return Response(result)
