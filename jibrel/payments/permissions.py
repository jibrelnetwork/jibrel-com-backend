import hmac
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CheckoutHMACSignature(BasePermission):
    def has_permission(self, request: Request, view: APIView):
        key = settings.CHECKOUT_PRIVATE_KEY
        if not key:
            raise ImproperlyConfigured('Key wasn\'t set')
        signature = hmac.new(key, msg=request.body, digestmod='').digest()
        if signature != request.headers.get('CKO-Signature'):
            logger.log(level=logging.INFO,
                       msg='Webhook is compromised. Webhook url should changed')
            raise AuthenticationFailed()
        return True
