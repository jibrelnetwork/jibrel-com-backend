from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from jibrel.campaigns.models import Offering
from jibrel.campaigns.serializers import OfferingSerializer
from jibrel.core.permissions import (
    IsCMS,
    IsKYCVerifiedUser
)


class CMSOfferingsAPIView(ListAPIView):
    authentication_classes: list = []
    permission_classes: list = [IsCMS]
    serializer_class = OfferingSerializer

    def get_queryset(self):
        return Offering.objects.filter(security__company__slug=self.kwargs['company'])


class OfferingsAPIView(CMSOfferingsAPIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [IsAuthenticated, IsKYCVerifiedUser]
