import typing

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from jibrel.core.errors import ConflictException

if typing.TYPE_CHECKING:
    from rest_framework.views import APIView


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
        last_kyc = request.user.profile.last_kyc
        if last_kyc and last_kyc.is_approved():
            return True
        raise ConflictException()
