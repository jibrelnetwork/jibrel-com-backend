from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jibrel.authentication.models import Profile
from jibrel.core.errors import ConflictException
from jibrel.core.rest_framework import WrapDataAPIViewMixin
from jibrel.core.utils import get_client_ip
from jibrel.kyc.models import BasicKYCSubmission
from jibrel.kyc.serializers import (
    AddedKYCDocumentsSerializer,
    BusinessKYCSubmissionSerializer,
    PersonalKYCSubmissionSerializer,
    PhoneRequestSerializer,
    UploadDocumentRequestSerializer,
    VerifyPhoneRequestSerializer
)
from jibrel.kyc.services import (
    check_phone_verification,
    get_added_documents,
    request_phone_verification,
    send_kyc_submitted_email,
    send_phone_verified_email,
    submit_basic_kyc,
    upload_document
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


class PhoneAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not request.user.is_email_confirmed or request.user.profile.is_phone_confirmed:
            raise ConflictException()
        serializer = PhoneRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.save(profile=request.user.profile)
        request_phone_verification(
            user=request.user,
            user_ip=get_client_ip(request),
            phone=phone
        )
        return Response()


class BasePhoneVerificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super(BasePhoneVerificationAPIView, self).check_permissions(request)
        if (
            not request.user.is_email_confirmed
            or not request.user.profile.phone
            or request.user.profile.is_phone_confirmed
        ):
            raise ConflictException()


class ResendSMSAPIView(BasePhoneVerificationAPIView):
    def post(self, request: Request) -> Response:
        request_phone_verification(
            user=request.user,
            user_ip=get_client_ip(request),
            phone=request.user.profile.phone,
        )
        return Response()


class CallPhoneAPIView(BasePhoneVerificationAPIView):
    def post(self, request: Request) -> Response:
        request_phone_verification(
            user=request.user,
            user_ip=get_client_ip(request),
            phone=request.user.profile.phone,
            channel=PhoneVerificationChannel.CALL
        )
        return Response()


class VerifyPhoneAPIView(BasePhoneVerificationAPIView):
    def post(self, request: Request) -> Response:
        serializer = VerifyPhoneRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        check_phone_verification(
            user=request.user,
            user_ip=get_client_ip(request),
            phone=request.user.profile.phone,
            pin=serializer.validated_data['pin']
        )
        send_phone_verified_email(request.user, get_client_ip(request))
        return Response()


class UploadDocumentAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = UploadDocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = upload_document(
            file=serializer.validated_data['file'],
            type=serializer.validated_data['type'],
            side=serializer.validated_data['side'],
            profile=request.user.profile,
        )
        return Response({
            'data': {
                'id': document_id
            }
        })


class PersonalKYCSubmissionAPIView(APIView):
    serializer_ = PersonalKYCSubmissionSerializer
    account_type = BasicKYCSubmission.PERSONAL

    def post(self, request):
        status = Profile.objects.get_basic_kyc_status(request.user.profile.pk)
        if status in {BasicKYCSubmission.APPROVED, BasicKYCSubmission.PENDING}:
            raise ConflictException()
        serializer = self.serializer_(data=request.data, context={'profile': request.user.profile})
        serializer.is_valid(raise_exception=True)
        submission = submit_basic_kyc(
            profile=request.user.profile,
            account_type=self.account_type,
            **serializer.validated_data,
        )
        send_kyc_submitted_email(
            user=request.user,
            user_ip=get_client_ip(request)
        )
        return Response({
            'data': {
                'id': str(submission.pk)
            }
        })


class BusinessKYCSubmissionAPIView(PersonalKYCSubmissionAPIView):
    serializer_ = BusinessKYCSubmissionSerializer
    account_type = BasicKYCSubmission.BUSINESS


class KYCSubmissionList(WrapDataAPIViewMixin, APIView):
    def get(self, request):
        return Response({
            'basic': {
                'status': Profile.objects.get_basic_kyc_status(request.user.profile.pk)
            }
        })


class KYCAddedDocumentsAPIView(WrapDataAPIViewMixin, APIView):
    def get(self, request: Request) -> Response:
        documents = get_added_documents(request.user.profile)
        return Response(
            AddedKYCDocumentsSerializer(documents, many=True).data
        )


class SubscribedCountriesAPIView(WrapDataAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request: Request):
        status = Profile.objects.get_basic_kyc_status(request.user.profile.pk)
        if status in {BasicKYCSubmission.APPROVED, BasicKYCSubmission.PENDING}:
            raise ConflictException()

    def get(self, request: Request) -> Response:
        # todo call autopilot
        return Response([])

    def put(self, request: Request) -> Response:
        # todo call autopilot
        return Response()
