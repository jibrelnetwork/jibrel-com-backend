import hashlib
from datetime import date
from uuid import UUID

from django.conf import settings
from django.core.files import File

from jibrel.authentication.models import Phone, Profile, User
from jibrel.core.errors import ConflictException, InvalidException
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
    email: str,
    street_address: str,
    apartment: str,
    post_code: str,
    city: str,
    country: str,
    occupation: str,
    occupation_other: str,
    income_source: str,
    income_source_other: str,
    passport_number: str,
    passport_expiration_date: date,
    passport_document: KYCDocument,
    proof_of_address_document: KYCDocument,
    aml_agreed: bool,
    ubo_confirmed: bool,
):
    print('AAA', first_name)
    submission = IndividualKYCSubmission.objects.create(
        profile=profile,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        birth_date=birth_date,
        nationality=nationality,
        email=email,
        street_address=street_address,
        apartment=apartment,
        post_code=post_code,
        city=city,
        country=country,
        occupation=occupation,
        occupation_other=occupation_other,
        income_source=income_source,
        income_source_other=income_source_other,
        passport_number=passport_number,
        passport_expiration_date=passport_expiration_date,
        passport_document=passport_document,
        proof_of_address_document=proof_of_address_document,
        aml_agreed=aml_agreed,
        ubo_confirmed=ubo_confirmed,
    )
    enqueue_onfido_routine(submission)
    return submission.pk


def submit_organisational_kyc(submission: OrganisationalKYCSubmission):
    enqueue_onfido_routine(submission)
    return submission.pk


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
