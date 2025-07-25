import hashlib
from datetime import date
from uuid import UUID

from django.conf import settings
from django.core.files import File

from jibrel.authentication.models import (
    Phone,
    Profile,
    User
)
from jibrel.core.errors import ConflictException
from jibrel.core.limits import (
    ResendVerificationSMSLimiter,
    UploadKYCDocumentLimiter
)
from jibrel.kyc.models import (
    IndividualKYCSubmission,
    KYCDocument,
    OrganisationalKYCSubmission
)
from jibrel.kyc.tasks import (
    check_verification_code,
    enqueue_onfido_routine,
    enqueue_onfido_routine_beneficiary,
    send_verification_code
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel

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
    """
    ResendVerificationSMSLimiter(user).is_throttled(raise_exception=True)
    send_verification_code.delay(
        phone_uuid=phone.uuid.hex,
        channel=channel.value,
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip}
    )
    phone.set_code_requested()


def check_phone_verification(
    user: User,
    user_ip: str,
    phone: Phone,
    pin: str,
) -> None:
    """Check phone verification by `pin`

    Creates ExternalServiceCallLog record and provide its uuid to task and send this task into queue

    Args:
        user:
        user_ip:
        phone:
        pin:
    """
    if phone.status not in (Phone.CODE_SENT, Phone.CODE_INCORRECT):
        raise ConflictException()
    verification = phone.verification_requests.created_in_last(
        VERIFICATION_SESSION_LIFETIME
    ).pending().order_by('created_at').last()
    if not verification:
        phone.status = Phone.EXPIRED
        phone.save()
        raise ConflictException()
    check_verification_code.apply_async(
        kwargs={
            'verification_id': str(verification.pk),
            'pin': pin,
            'task_context': {
                'user_id': user.uuid.hex,
                'user_ip_address': user_ip
            }
        },
        expires=settings.TWILIO_REQUEST_TIMEOUT
    )
    phone.set_code_submitted()


def upload_document(
    file: File,
    profile: Profile,
) -> UUID:
    UploadKYCDocumentLimiter(profile.user).is_throttled(raise_exception=True)
    checksum = hashlib.md5(file.read()).hexdigest()
    document = KYCDocument.objects.create(
        file=file,
        profile=profile,
        checksum=checksum,
    )
    return document.uuid


def submit_individual_kyc(
    *,
    profile: Profile,
    first_name: str,
    middle_name: str,
    last_name: str,
    birth_date: date,
    nationality: str,
    street_address: str,
    apartment: str,
    post_code: str,
    city: str,
    country: str,
    occupation: str,
    income_source: str,
    passport_number: str,
    passport_expiration_date: date,
    passport_document: KYCDocument,
    proof_of_address_document: KYCDocument,
):
    submission = IndividualKYCSubmission.objects.create(
        profile=profile,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        birth_date=birth_date,
        nationality=nationality,
        street_address=street_address,
        apartment=apartment,
        post_code=post_code,
        city=city,
        country=country,
        occupation=occupation,
        income_source=income_source,
        passport_number=passport_number,
        passport_expiration_date=passport_expiration_date,
        passport_document=passport_document,
        proof_of_address_document=proof_of_address_document,
    )
    submission.profile.kyc_status = Profile.KYC_PENDING
    submission.profile.save()
    enqueue_onfido_routine(submission).delay()
    return submission


def submit_organisational_kyc(submission: OrganisationalKYCSubmission):
    submission.profile.kyc_status = Profile.KYC_PENDING
    submission.profile.save()
    enqueue_onfido_routine(submission).delay()
    for beneficiary in submission.beneficiaries.all():
        enqueue_onfido_routine_beneficiary(beneficiary).delay()
    return submission
