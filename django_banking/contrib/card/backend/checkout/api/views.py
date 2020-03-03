from rest_framework.generics import RetrieveAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView

from django_banking.contrib.card.backend.checkout.api.serializers import CheckoutCardSerializer, \
    CheckoutChargeSerializer, CheckoutTokenSerializer


class CardTokenizeAPIView(APIView):
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)
    serializer_class = CheckoutTokenSerializer
    serializer_response_class = CheckoutCardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.POST)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        data = self.serializer_response_class(

        )

        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)


class CardDepositAPIView(CreateAPIView):
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)
    serializer_class = CheckoutChargeSerializer

    def post(self, request, card_id):
        raise NotImplementedError()


class CardChargeAPIView(RetrieveAPIView):

    """Get operation id for tap charge id.
    """

    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)
    serializer_class = CheckoutChargeSerializer

    def post(self, request, card_id):
        raise NotImplementedError()
