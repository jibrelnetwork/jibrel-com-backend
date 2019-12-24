import logging
from uuid import UUID

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    get_object_or_404
)
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from ccwt.core.exceptions import NonSupportedCountryException
from .. import logger
from ..core.api.pagination import CustomCursorPagination
from ..limitations.utils import get_user_limits
from .serializers import (
    AccountBalanceSerializer,
    AssetSerializer,
    LimitsSerializer,
    OperationSerializer,
    UploadConfirmationRequestSerializer
)
from ..models import Asset, UserAccount, Operation
from ccwt.models import PaymentOperation


class AssetsListAPIView(ListAPIView):
    serializer_class = AssetSerializer

    def get_queryset(self):
        qs = Asset.objects.all()
        if 'country' in self.request.GET:
            qs = qs.filter(country=self.request.GET['country'].upper())
        return qs


class OperationViewSet(ReadOnlyModelViewSet):
    serializer_class = OperationSerializer

    pagination_class = CustomCursorPagination
    page_size_query_param = 'cursor'  # TODO: WTF? Why `cursor`?

    def get_queryset(self):
        try:
            qs = PaymentOperation.objects.with_amounts(
                self.request.user
            ).for_user(
                self.request.user,
                only_allowed_assets=False
            ).order_by('-created_at')
        except NonSupportedCountryException:
            qs = PaymentOperation.objects.none()
        return qs

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if not response.exception:
            response.data = {
                'data': response.data
            }
        return response


class UploadOperationConfirmationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_accounts = UserAccount.objects.get_user_accounts(request.user)
        operation = get_object_or_404(
            Operation, transactions__account__in=user_accounts, pk=pk
        )
        serializer = UploadConfirmationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(operation=operation)
        return Response(status=status.HTTP_201_CREATED)


class PaymentLimitsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = LimitsSerializer(get_user_limits(request.user), many=True)
        return Response({
            'data': serializer.data
        })



