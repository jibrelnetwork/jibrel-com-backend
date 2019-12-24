from rest_framework import mixins
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from jibrel.authentication.models import (
    Phone,
    Profile
)
from jibrel.core.errors import ConflictException
from jibrel.core.permissions import IsEmailConfirmed
from jibrel.core.rest_framework import WrapDataAPIViewMixin
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
    submit_individual_kyc,
    submit_organisational_kyc,
    upload_document
)
from jibrel.kyc.tasks import send_kyc_submitted_mail
from jibrel.notifications.phone_verification import PhoneVerificationChannel

from .models import BaseKYCSubmission


class PhoneConflictViewMixin:
    def handle_exception(self, exc):
        if isinstance(exc, ConflictException):
            exc.data = PhoneSerializer(self.request.user.profile.phone).data
        return super().handle_exception(exc)


class IsPhoneUnconfirmed(BasePermission):
    def has_permission(self, request, view):
        if request.user.profile.is_phone_confirmed:
            raise ConflictException()
        return True


class PhoneAPIView(
    PhoneConflictViewMixin,
    WrapDataAPIViewMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericAPIView
):
    permission_classes = [IsAuthenticated, IsEmailConfirmed, IsPhoneUnconfirmed]

    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return super(PhoneAPIView, self).get_permissions()

    def get_object(self):
        return self.request.user.profile.phone

    def post(self, request: Request) -> Response:
        if self.get_object():
            raise ConflictException()

        return self.create(request)

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)

    def get(self, request: Request) -> Response:
        return self.retrieve(request)

    def put(self, request: Request) -> Response:
        if not self.get_object():
            raise ConflictException()

        return self.update(request)

    def perform_update(self, serializer):
        serializer.instance = None  # to create new phone instead old
        serializer.save(profile=self.request.user.profile)


class BasePhoneVerificationAPIView(PhoneConflictViewMixin, APIView):
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
    serializer_class = IndividualKYCSubmissionSerializer

    def post(self, request):
        profile = request.user.profile
        if profile.kyc_status != Profile.KYC_UNVERIFIED:
            raise ConflictException()
        serializer = self.serializer_class(data=request.data, context={'profile': request.user.profile})
        serializer.is_valid(raise_exception=True)
        kyc_submission_id = submit_individual_kyc(
            profile=request.user.profile,
            first_name=serializer.validated_data.get('first_name'),
            middle_name=serializer.validated_data.get('middle_name', ''),
            last_name=serializer.validated_data.get('last_name'),
            birth_date=serializer.validated_data.get('birth_date'),
            nationality=serializer.validated_data.get('nationality'),
            street_address=serializer.validated_data.get('street_address'),
            apartment=serializer.validated_data.get('apartment', ''),
            post_code=serializer.validated_data.get('post_code', ''),
            city=serializer.validated_data.get('city'),
            country=serializer.validated_data.get('country'),
            occupation=serializer.validated_data.get('occupation', ''),
            income_source=serializer.validated_data.get('incomeSource', ''),
            passport_number=serializer.validated_data.get('passport_number'),
            passport_expiration_date=serializer.validated_data.get('passport_expiration_date'),
            passport_document=serializer.validated_data.get('passport_document'),
            proof_of_address_document=serializer.validated_data.get('proof_of_address_document'),
            is_agreed_risks=serializer.validated_data.get('isAgreedRisks'),
        )
        send_kyc_submitted_mail.delay(
            account_type=BaseKYCSubmission.INDIVIDUAL,
            kyc_submission_id=kyc_submission_id
        )
        return Response({'data': {'id': kyc_submission_id}})


class IndividualKYCValidateAPIView(APIView):
    serializer_class = IndividualKYCSubmissionSerializer
    # https://jibrelnetwork.atlassian.net/wiki/spaces/JIB/pages/1030291484/KYC
    validation_steps = (
        (
            'firstName',
            'lastName',
            'middleName',
            'alias',
            'birthDate',
            'nationality',
            'passportNumber',
            'passportExpirationDate',
            'passportDocument',
        ),
        (
            'streetAddress',
            'apartment',
            'city',
            'postCode',
            'country',
            'proofOfAddressDocument',
        ),
        (
            'occupation',
            'incomeSource',
            'isAgreedRisks',
        ),
    )

    def post(self, request):
        try:
            fields_to_validate = self.validation_steps[int(request.data['step'])]
        except (KeyError, IndexError, TypeError):
            return Response({'data': {'valid': False, 'errors': {'step': 'invalid step'}}}, status=HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data, context={'profile': request.user.profile})

        errors = {}
        if not serializer.is_valid(raise_exception=False):
            errors = {k: v for k, v in serializer.errors.items() if k in fields_to_validate}

        if errors:
            return Response({'data': {'valid': False, 'errors': errors}}, status=HTTP_400_BAD_REQUEST)

        return Response({'data': {'valid': True}})


class OrganisationalKYCSubmissionAPIView(APIView):
    parser_classes = [JSONParser]
    serializer_class = OrganisationalKYCSubmissionSerializer

    def post(self, request):
        profile = request.user.profile
        if profile.kyc_status != Profile.KYC_UNVERIFIED:
            raise ConflictException()
        serializer = self.serializer_class(data=request.data, context={'profile': request.user.profile})
        serializer.is_valid(raise_exception=True)
        kyc_submission = serializer.save(profile=request.user.profile)
        submit_organisational_kyc(kyc_submission)
        send_kyc_submitted_mail.delay(
            account_type=BaseKYCSubmission.BUSINESS,
            kyc_submission_id=kyc_submission.pk
        )
        return Response({'data': {'id': kyc_submission.pk}})


class OrganisationalKYCValidateAPIView(IndividualKYCValidateAPIView):
    parser_classes = [JSONParser]
    serializer_class = OrganisationalKYCSubmissionSerializer
    # https://jibrelnetwork.atlassian.net/wiki/spaces/JIB/pages/1030291484/KYC
    validation_steps = (  # type: ignore
        (
            'companyName',
            'tradingName',
            'dateOfIncorporation',
            'placeOfIncorporation',
            'commercialRegister',
            'shareholderRegister',
            'articlesOfIncorporation',
        ),
        (
            # nested fields cannot be separated
            'companyAddressRegistered',
            'companyAddressPrincipal',
        ),
        (
            'firstName',
            'lastName',
            'middleName',
            'birthDate',
            'nationality',
            'phoneNumber',
            'email',
            'streetAddress',
            'apartment',
            'city',
            'postCode',
            'country',
            'passportNumber',
            'passportExpirationDate',
            'passportDocument',
            'proofOfAddressDocument',
        ),
        (
            'beneficiaries'
        ),
        (
            'directors',
            'isAgreedRisks',
        ),
    )
