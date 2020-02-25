import typing

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from jibrel.core.errors import ConflictException

if typing.TYPE_CHECKING:
    from rest_framework.views import APIView


class IsCMS(BasePermission):
    def has_permission(self, request: Request, view: 'APIView'):
        key = settings.CMS_INTEGRATION_PRIVATE_KEY
        if not key:
            raise ImproperlyConfigured('Key wasn\'t set')
        token = request.headers.get('Authorization')
        if token != f'Bearer {key}':
            raise AuthenticationFailed()
        return True


class IsEmailConfirmed(BasePermission):
    def has_permission(self, request: Request, view: 'APIView'):
        if not request.user.is_email_confirmed:
            raise ConflictException()
        return True


class IsConfirmedUser(BasePermission):
    def has_permission(self, request: Request, view: 'APIView'):
        if not (request.user.is_email_confirmed and request.user.profile.is_phone_confirmed):
            raise ConflictException()
        return True


class IsKYCVerifiedUser(IsConfirmedUser):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.profile.is_kyc_verified:
            return True
        raise ConflictException()
