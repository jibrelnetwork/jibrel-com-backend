from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView

from jibrel.campaigns.models import Offering
from jibrel.campaigns.serializers import CMSOfferingSerializer
from django.conf import settings


class CMSOfferingsAPIView(ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CMSOfferingSerializer

    def authenticate(self):
        token = self.request.headers.get('Authentication')
        if token != f'Bearer {settings.CMS_INTEGRATION_PRIVATE_KEY}':
            raise AuthenticationFailed()

    def dispatch(self, request, *args, **kwargs):
        self.authenticate()
        return super(CMSOfferingsAPIView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Offering.objects.filter(security__company__slug=self.kwargs['company'])
