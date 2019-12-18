from django.contrib.auth import (
    authenticate,
    login,
    logout
)
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import (
    RetrieveAPIView,
    get_object_or_404
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jibrel.authentication.models import Profile
from jibrel.authentication.serializers import (
    ActivateResetPasswordSerializer,
    ChangePasswordRequestSerializer,
    LoginRequestSerializer,
    RegisterRequestSerializer,
    RequestResetPasswordSerializer,
    ResetPasswordSerializer,
    SetLanguageRequestSerializer,
    UserProfileResponseSerializer,
    VerifyEmailRequestSerializer
)
from jibrel.authentication.services import (
    activate_password_reset,
    change_password,
    register,
    request_password_reset,
    reset_password_complete,
    send_verification_email,
    verify_user_email_by_key
)
from jibrel.core.errors import EmailVerifiedException
from jibrel.core.limits import get_limits
from jibrel.core.rest_framework import WrapDataAPIViewMixin
from jibrel.core.utils import get_client_ip


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        request_serializer = RegisterRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        profile = register(
            email=request_serializer.data['email'],
            password=request_serializer.data['password'],
            username=f'{request_serializer.data["firstName"]} {request_serializer.data["lastName"]}'[:128],
            first_name=request_serializer.data['lastName'],
            last_name=request_serializer.data['firstName'],
            is_agreed_terms=request_serializer.data['isAgreedTerms'],
            is_agreed_privacy_policy=request_serializer.data['isAgreedPrivacyPolicy'],
            language=request_serializer.data['language'],
        )
        login(request, profile.user)
        send_verification_email(profile.user, get_client_ip(request))
        response_serializer = UserProfileResponseSerializer(profile)
        return Response({
            'data': response_serializer.data
        })


class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = VerifyEmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_user_email_by_key(serializer.validated_data['key'])
        login(request, user)
        return Response()


class ConfirmationEmailResendAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_email_confirmed:
            raise EmailVerifiedException.for_field('email')
        send_verification_email(request.user, get_client_ip(request))
        return Response()


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        request_serializer = LoginRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        user = authenticate(request, **request_serializer.data)
        if not user:
            raise PermissionDenied()
        login(request, user)
        response_serializer = UserProfileResponseSerializer(user.profile)
        return Response({
            'data': response_serializer.data
        })


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response()


class ChangePasswordAPIView(APIView):
    def post(self, request: Request):
        serializer = ChangePasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_password(
            user=request.user,
            old_password=serializer.validated_data['oldPassword'],
            new_password=serializer.validated_data['newPassword'],
        )
        login(request, request.user)
        return Response()


class RequestResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RequestResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(
            user_ip=get_client_ip(request),
            email=serializer.validated_data['email']
        )
        return Response()


class ActivateResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ActivateResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activate_password_reset(
            key=serializer.validated_data['key']
        )
        return Response()


class CompleteResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password_complete(
            key=serializer.validated_data['key'],
            password=serializer.validated_data['password'],
        )
        return Response()


class UserProfileAPIView(WrapDataAPIViewMixin, RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileResponseSerializer

    def get_object(self):
        return get_object_or_404(
            Profile.objects.select_related('user'),
            user=self.request.user,
        )


class LimitsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(
            get_limits(request.user)
        )


class SetLanguageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SetLanguageRequestSerializer(instance=request.user.profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()
