from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from jibrel.campaigns.enum import OfferingStatus
from jibrel.campaigns.models import Offering
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.errors import ConflictException
from jibrel.core.permissions import (
    IsCMS,
    IsKYCVerifiedUser
)


class CMSOfferingsAPIView(ListAPIView):
    authentication_classes: list = []
    permission_classes: list = [IsCMS]
    serializer_class = OfferingSerializer

    def get_queryset(self):
        return Offering.objects.filter(
            security__company__slug=self.kwargs['company']
        ).exclude(status=OfferingStatus.DRAFT)


class OfferingAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    serializer_class = OfferingSerializer
    lookup_field = 'uuid'
    lookup_url_kwarg = 'offering_id'

    def get_queryset(self):
        return Offering.objects.exclude(status=OfferingStatus.DRAFT)


class OfferingsAPIView(CMSOfferingsAPIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]


class ActiveOfferingAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
    serializer_class = OfferingSerializer

    def get_object(self):
        qs = self.get_queryset()
        # There is always only one object at this queryset. By design.
        obj = get_object_or_404(qs)
        if self.request.user.applications.filter(
            offering__security__company__slug=self.kwargs['company']
        ).active().exists():
            raise ConflictException()
        return obj

    def get_queryset(self):
        return Offering.objects.filter(security__company__slug=self.kwargs['company']).active()
