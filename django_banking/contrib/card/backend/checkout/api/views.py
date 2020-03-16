from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from django_banking.contrib.card.backend.checkout.api.serializers import (
    CheckoutTokenSerializer
)


class CardDepositAPIView(CreateAPIView):
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)
    serializer_class = CheckoutTokenSerializer

    def post(self, *args, **kwargs):
        raise NotImplementedError()
