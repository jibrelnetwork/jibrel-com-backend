
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_banking.contrib.card.backend.tap.permissions import IsCardOwner


class CardListAPIView(APIView):

    """List saved plastic cards saved by authenticated user.
    """

    throttle_scope = 'payments'
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raise NotImplementedError()


class CardDepositAPIView(APIView):

    """Start TAP deposit routine.

    Create charge on tap side, and return redirect url for user (in case of
    3d secure) or transaction id if already charged.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsCardOwner)

    def post(self, request, card_id):
        raise NotImplementedError()


class CardChargeAPIView(APIView):

    """Get operation id for tap charge id.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated, IsCardOwner)

    def post(self, request, card_id):
        raise NotImplementedError()
