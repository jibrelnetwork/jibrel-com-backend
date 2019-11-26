import hashlib
from datetime import date
from typing import List, Optional
from uuid import UUID

from django.conf import settings
from django.core.files import File
from django.utils import timezone

from jibrel.authentication.models import Phone, Profile, User
from jibrel.core.errors import ConflictException, InvalidException
from jibrel.core.limits import (
    ResendVerificationSMSLimiter,
    UploadKYCDocumentLimiter
)
from jibrel.kyc.models import (
    BasicKYCSubmission,
    Document,
    PersonalDocument,
    PersonalDocumentType
)
from jibrel.kyc.tasks import (
    check_verification_code,
    enqueue_onfido_routine,
    send_verification_code
)
from jibrel.notifications.email import (
    KYCSubmittedEmailMessage,
    PhoneVerifiedEmailMessage
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel
from jibrel.notifications.tasks import send_mail

SEND_VERIFICATION_TIME_LIMIT = settings.SEND_VERIFICATION_TIME_LIMIT
FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT = settings.FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT
FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT = settings.FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT
VERIFICATION_SESSION_LIFETIME = settings.VERIFICATION_SESSION_LIFETIME


def request_phone_verification(
    user: User,
    user_ip: str,
    phone: Phone,
    channel: PhoneVerificationChannel = PhoneVerificationChannel.SMS,
) -> None:
    """Request phone verification process

    Creates ExternalServiceCallLog record and provide its uuid
    to task and send this task into queue

    Args:
        user:
        user_ip:
        phone:
        channel:

    Returns:
        datetime when function may be called for user next time
    """
    ResendVerificationSMSLimiter(user).is_throttled(raise_exception=True)
    send_verification_code.delay(
        phone_uuid=phone.uuid.hex,
        channel=channel.value,
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip}
    )


def check_phone_verification(
    user: User,
    user_ip: str,
    phone: Phone,
    pin: str,
) -> None:
    """Check phone verification by `pin`

    Creates ExternalServiceCallLog record and provide its uuid to task and send this task into queue

    Notes
        This function synchronous and waits until task completes

    Args:
        user:
        user_ip:
        phone:
        pin:

    Returns:
        datetime when function may be called for user next time
    """

    verification = phone.verification_requests.created_in_last(
        VERIFICATION_SESSION_LIFETIME
    ).pending().order_by('created_at').last()
    if not verification:
        raise ConflictException()
    result = check_verification_code.apply_async(
        kwargs={
            'verification_sid': verification.verification_sid,
            'pin': pin,
            'task_context': {
                'user_id': user.uuid.hex,
                'user_ip_address': user_ip
            }
        },
        expires=settings.TWILIO_REQUEST_TIMEOUT
    )

    try:
        is_verified = result.get(timeout=settings.TWILIO_REQUEST_TIMEOUT)
    except TimeoutError:
        raise InvalidException('pin', 'Pin check timeout', 'Timeout')

    if not is_verified:
        raise InvalidException('pin')
    phone.is_confirmed = True
    phone.save()
    return None


def upload_document(
    file: File,
    type: str,
    side: str,
    profile: Profile,
) -> UUID:
    UploadKYCDocumentLimiter(profile.user).is_throttled(raise_exception=True)
    checksum = hashlib.md5(file.read()).hexdigest()
    document = Document.objects.create(
        file=file,
        type=type,
        side=side,
        profile=profile,
        checksum=checksum,
    )
    return document.uuid


def submit_basic_kyc(
    *,
    profile: Profile,
    citizenship: str,
    residency: str,
    first_name: str,
    middle_name: str,
    last_name: str,
    birth_date: Optional[date] = None,
    birth_date_hijri: Optional[str] = None,
    personal_id_type: str,
    personal_id_number: str,
    personal_id_doe: Optional[date] = None,
    personal_id_doe_hijri: Optional[str] = None,
    personal_id_document_front: Document,
    personal_id_document_back: Optional[Document] = None,
    residency_visa_number: str = None,
    residency_visa_doe: Optional[date] = None,
    residency_visa_doe_hijri: Optional[date] = None,
    residency_visa_document: Optional[Document] = None,
    is_agreed_aml_policy: bool,
    is_birth_date_hijri: bool,
    is_confirmed_ubo: bool,
    is_personal_id_doe_hijri: bool,
    is_residency_visa_doe_hijri: bool
) -> BasicKYCSubmission:
    submission = BasicKYCSubmission.objects.create(
        profile=profile,
        citizenship=citizenship,
        residency=residency,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        birth_date=birth_date,
        birth_date_hijri=birth_date_hijri,
        personal_id_type=personal_id_type,
        personal_id_number=personal_id_number,
        personal_id_doe=personal_id_doe,
        personal_id_doe_hijri=personal_id_doe_hijri,
        personal_id_document_front=personal_id_document_front,
        personal_id_document_back=personal_id_document_back,
        residency_visa_number=residency_visa_number,
        residency_visa_doe=residency_visa_doe,
        residency_visa_doe_hijri=residency_visa_doe_hijri,
        residency_visa_document=residency_visa_document,
        is_agreed_aml_policy=is_agreed_aml_policy,
        is_birth_date_hijri=is_birth_date_hijri,
        is_confirmed_ubo=is_confirmed_ubo,
        is_personal_id_doe_hijri=is_personal_id_doe_hijri,
        is_residency_visa_doe_hijri=is_residency_visa_doe_hijri,
        transitioned_at=timezone.now(),
    )
    enqueue_onfido_routine(submission)
    return submission


def get_added_documents(profile: Profile) -> List[PersonalDocument]:
    documents = []
    last_approved_basic: Optional[BasicKYCSubmission] = BasicKYCSubmission.objects.filter(
        profile=profile,
        status=BasicKYCSubmission.APPROVED,
    ).order_by('-created_at').first()
    if last_approved_basic is not None:
        documents.append(
            PersonalDocument(
                type=PersonalDocumentType(last_approved_basic.personal_id_type),
                doe=last_approved_basic.personal_id_doe,
                first_name=last_approved_basic.first_name,
                middle_name=last_approved_basic.middle_name,
                last_name=last_approved_basic.last_name,
            )
        )
        if last_approved_basic.residency_visa_number:
            documents.append(
                PersonalDocument(
                    type=PersonalDocumentType.RESIDENCY_VISA,
                    doe=last_approved_basic.residency_visa_doe,
                    first_name=last_approved_basic.first_name,
                    middle_name=last_approved_basic.middle_name,
                    last_name=last_approved_basic.last_name,
                )
            )
    return documents


def send_kyc_submitted_email(user: User, user_ip: str):
    rendered = KYCSubmittedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username
    })
    send_mail.delay(
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip},
        recipient=user.email,
        **rendered.serialize()
    )


def send_phone_verified_email(user: User, user_ip: str):
    rendered = PhoneVerifiedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username,
        'masked_phone_number': user.profile.phone.number[-4:],
        'email': user.email,
    })
    send_mail.delay(
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip},
        recipient=user.email,
        **rendered.serialize()
    )
