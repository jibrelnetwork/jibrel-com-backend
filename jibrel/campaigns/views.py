from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView

from jibrel.campaigns.models import Offering
from jibrel.campaigns.serializers import CMSOfferingSerializer


class CMSOfferingsAPIView(ListAPIView):
    authentication_classes: list = []
    permission_classes: list = []
    serializer_class = CMSOfferingSerializer

    def authenticate(self):
        key = settings.CMS_INTEGRATION_PRIVATE_KEY
        if not key:
            raise ImproperlyConfigured('Key wasn\'t set')
        token = self.request.headers.get('Authentication')
        if token != f'Bearer {key}':
            raise AuthenticationFailed()

    def dispatch(self, request, *args, **kwargs):
        self.authenticate()
        return super(CMSOfferingsAPIView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Offering.objects.filter(security__company__slug=self.kwargs['company'])
