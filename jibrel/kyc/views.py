from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jibrel.core.errors import ConflictException
from jibrel.core.utils import get_client_ip
from jibrel.kyc.serializers import (
    IndividualKYCSubmissionSerializer,
    OrganisationalKYCSubmissionSerializer,
    PhoneSerializer,
    UploadDocumentRequestSerializer,
    VerifyPhoneRequestSerializer
)
from jibrel.kyc.services import (
    check_phone_verification,
    request_phone_verification,
    send_phone_verified_email,
    submit_individual_kyc,
    submit_organisational_kyc,
    upload_document
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


class PhoneAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PhoneSerializer

    def post(self, request: Request) -> Response:
        if not request.user.is_email_confirmed or request.user.profile.is_phone_confirmed:
            raise ConflictException()
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=request.user.profile)
        return Response()

    def get(self, request: Request) -> Response:
        serializer = self.serializer_class(request.user.profile.phone)
        return Response(serializer.data)


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
        return Response()


class UploadDocumentAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = UploadDocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = upload_document(
            file=serializer.validated_data['file'],
            profile=request.user.profile,
        )
        return Response({
            'data': {
                'id': document_id
            }
        })


class IndividualKYCSubmissionAPIView(APIView):
    def post(self, request):
        serializer = IndividualKYCSubmissionSerializer(data=request.data, context={'profile': request.user.profile})
        serializer.is_valid(raise_exception=True)
        submit_individual_kyc(
            profile=request.user.profile,
            first_name=serializer.validated_data.get('first_name'),
            middle_name=serializer.validated_data.get('middle_name', ''),
            last_name=serializer.validated_data.get('last_name'),
            birth_date=serializer.validated_data.get('birth_date'),
            nationality=serializer.validated_data.get('nationality'),
            email=serializer.validated_data.get('email'),
            street_address=serializer.validated_data.get('street_address'),
            apartment=serializer.validated_data.get('apartment', ''),
            post_code=serializer.validated_data.get('post_code', ''),
            city=serializer.validated_data.get('city'),
            country=serializer.validated_data.get('country'),
            occupation=serializer.validated_data.get('occupation', ''),
            occupation_other=serializer.validated_data.get('occupationOther', ''),
            income_source=serializer.validated_data.get('incomeSource', ''),
            income_source_other=serializer.validated_data.get('incomeSourceOther', ''),
            passport_number=serializer.validated_data.get('passport_number'),
            passport_expiration_date=serializer.validated_data.get('passport_expiration_date'),
            passport_document=serializer.validated_data.get('passport_document'),
            proof_of_address_document=serializer.validated_data.get('proof_of_address_document'),
            aml_agreed=serializer.validated_data.get('amlAgreed'),
            ubo_confirmed=serializer.validated_data.get('uboConfirmed'),
        )

        # todo send mail
        return Response()


class OrganisationalKYCSubmissionAPIView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = OrganisationalKYCSubmissionSerializer(data=request.data, context={'profile': request.user.profile})
        serializer.is_valid(raise_exception=True)
        kyc_submission = serializer.save(profile=request.user.profile)
        submit_organisational_kyc(kyc_submission)
        # todo send mail
        return Response({'data': {'id': kyc_submission.pk}})
