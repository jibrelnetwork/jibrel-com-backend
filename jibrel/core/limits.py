from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta
)
from enum import Enum
from typing import (
    Any,
    Dict,
    Optional
)

from django.conf import settings
from django.db.models.functions import Now
from django.utils import timezone
from rest_framework.exceptions import Throttled

from jibrel.authentication.models import (
    OneTimeToken,
    Phone,
    User
)
from jibrel.kyc.models import (
    KYCDocument,
    PhoneVerification
)


@dataclass
class Limit:
    left_seconds: int
    left_attempts: Optional[int]


class LimitType(Enum):
    RESEND_VERIFICATION_EMAIL = 'resend_verification_email'
    RESEND_VERIFICATION_SMS = 'resend_verification_sms'
    RESEND_VERIFICATION_CALL = 'resend_verification_call'
    VERIFY_PHONE = 'verify_phone'
    UPLOAD_KYC_DOCUMENT = 'upload_kyc_document'
    RESET_PASSWORD = 'reset_password'


class Limiter:
    def __init__(self, user: User):
        self.user = user

    @property
    def type(self) -> LimitType:
        raise NotImplementedError

    @property
    def is_permitted(self) -> bool:
        raise NotImplementedError

    def get_limit(self) -> Limit:
        raise NotImplementedError

    @property
    def limit(self) -> Optional[Limit]:
        if not self.is_permitted:
            return None
        return self.get_limit()

    def is_throttled(self, raise_exception=True) -> bool:
        limit = self.get_limit()
        if not limit:
            return True
        if limit.left_seconds > 0 and raise_exception:
            raise Throttled()
        return limit.left_seconds > 0


class ResendVerificationEmailLimiter(Limiter):
    type = LimitType.RESEND_VERIFICATION_EMAIL

    VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT = settings.VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT
    VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT = settings.VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT
    VERIFY_EMAIL_SEND_TOKEN_TIMEOUT = settings.VERIFY_EMAIL_SEND_TOKEN_TIMEOUT

    @property
    def is_permitted(self) -> bool:
        return not self.user.is_email_confirmed

    def get_limit(self) -> Limit:
        attempts: int = OneTimeToken.objects.filter(
            user=self.user,
            created_at__gte=Now() - timedelta(seconds=self.VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT),
            operation_type=OneTimeToken.EMAIL_VERIFICATION,
        ).count()
        last_call_ts: Optional[datetime] = OneTimeToken.objects.filter(
            user=self.user,
            operation_type=OneTimeToken.EMAIL_VERIFICATION,
        ).order_by('-created_at').values_list('created_at', flat=True).first()
        if not last_call_ts:
            next_call_in = timezone.now()
        elif attempts >= self.VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT:
            next_call_in = last_call_ts + timedelta(seconds=self.VERIFY_EMAIL_SEND_TOKEN_TIME_LIMIT)
        else:
            next_call_in = last_call_ts + timedelta(seconds=self.VERIFY_EMAIL_SEND_TOKEN_TIMEOUT)
        left_time = max((next_call_in - timezone.now()).total_seconds(), 0)
        return Limit(
            left_attempts=self.VERIFY_EMAIL_SEND_TOKEN_ATTEMPT_COUNT - attempts,
            left_seconds=int(left_time)
        )


class ResendVerificationSMSLimiter(Limiter):
    type = LimitType.RESEND_VERIFICATION_SMS

    SEND_VERIFICATION_TIME_LIMIT = settings.SEND_VERIFICATION_TIME_LIMIT
    FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT = settings.FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT
    FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT = settings.FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT
    VERIFICATION_SESSION_LIFETIME = settings.VERIFICATION_SESSION_LIFETIME

    @property
    def is_permitted(self) -> bool:
        return self.user.profile.phone and not self.user.profile.is_phone_confirmed

    def get_limit(self) -> Limit:
        phone = self.user.profile.phone
        last_request_ts = Phone.objects.filter(
            profile_id=phone.profile_id
        ).order_by('-code_requested_at').values_list('code_requested_at', flat=True).first()

        last_verification = PhoneVerification.objects.filter(
            phone__profile=phone.profile,
            phone__number=phone.number,
        ).order_by('-created_at').first()
        failed_attempts = PhoneVerification.objects.filter(
            phone__profile=self.user.profile,
            phone__number=phone.number,
            created_at__gte=Now() - timedelta(seconds=self.FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT)
        ).failed().count()
        if not last_verification:
            if not last_request_ts:
                next_call_in = timezone.now()
            else:
                next_call_in = last_request_ts + timedelta(seconds=self.SEND_VERIFICATION_TIME_LIMIT)
        elif failed_attempts >= self.FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT:
            next_call_in = last_verification.created_at + timedelta(
                seconds=self.FAILED_SEND_VERIFICATION_ATTEMPTS_TIME_LIMIT)
        elif last_verification.status == PhoneVerification.MAX_ATTEMPTS_REACHED:
            next_call_in = last_verification.created_at + timedelta(seconds=self.VERIFICATION_SESSION_LIFETIME)
        else:
            if not last_request_ts:
                next_call_in = timezone.now()
            else:
                next_call_in = last_request_ts + timedelta(seconds=self.SEND_VERIFICATION_TIME_LIMIT)
        return Limit(
            left_seconds=int(
                max((next_call_in - timezone.now()).total_seconds(), 0)
            ),
            left_attempts=self.FAILED_SEND_VERIFICATION_ATTEMPTS_COUNT - failed_attempts,
        )


class ResendVerificationCallLimiter(ResendVerificationSMSLimiter):
    type = LimitType.RESEND_VERIFICATION_CALL


class UploadKYCDocumentLimiter(Limiter):
    type = LimitType.UPLOAD_KYC_DOCUMENT

    UPLOAD_KYC_DOCUMENT_COUNT = settings.UPLOAD_KYC_DOCUMENT_COUNT
    UPLOAD_KYC_DOCUMENT_TIME_LIMIT = settings.UPLOAD_KYC_DOCUMENT_TIME_LIMIT

    @property
    def is_permitted(self) -> bool:
        return self.user.is_email_confirmed and self.user.profile.is_phone_confirmed

    def get_limit(self) -> Limit:
        attempts_qs = KYCDocument.objects.filter(
            profile=self.user.profile, created_at__gte=Now() - timedelta(seconds=self.UPLOAD_KYC_DOCUMENT_TIME_LIMIT)
        )
        attempts = attempts_qs.count()
        if attempts >= self.UPLOAD_KYC_DOCUMENT_COUNT:
            first_attempt = attempts_qs.order_by('created_at').first()
            left_seconds = (
                first_attempt.created_at
                + timedelta(seconds=self.UPLOAD_KYC_DOCUMENT_TIME_LIMIT)
                - timezone.now()
            ).seconds
        else:
            left_seconds = 0
        return Limit(
            left_seconds=left_seconds,
            left_attempts=max(self.UPLOAD_KYC_DOCUMENT_COUNT - attempts, 0)
        )


class ResetPasswordLimiter(Limiter):
    type = LimitType.RESET_PASSWORD
    is_permitted = True

    FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME = settings.FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME
    FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT = settings.FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT
    FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT = settings.FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT
    FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT = settings.FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT

    def get_limit(self) -> Limit:
        attempts: int = OneTimeToken.objects.filter(
            user=self.user,
            created_at__gte=Now() - timedelta(seconds=self.FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME),
            operation_type=OneTimeToken.PASSWORD_RESET_ACTIVATE,
        ).count()
        last_call_ts: Optional[datetime] = OneTimeToken.objects.filter(
            user=self.user,
            operation_type=OneTimeToken.PASSWORD_RESET_ACTIVATE,
        ).order_by('-created_at').values_list('created_at', flat=True).first()
        if not last_call_ts:
            next_call_in = timezone.now()
        elif attempts >= self.FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT:
            next_call_in = last_call_ts + timedelta(seconds=self.FORGOT_PASSWORD_SEND_TOKEN_TIME_LIMIT)
        else:
            next_call_in = last_call_ts + timedelta(seconds=self.FORGOT_PASSWORD_SEND_TOKEN_TIMEOUT)
        left_time = max((next_call_in - timezone.now()).total_seconds(), 0)
        return Limit(
            left_attempts=self.FORGOT_PASSWORD_SEND_TOKEN_ATTEMPT_COUNT - attempts,
            left_seconds=int(left_time)
        )


def serialize_limit(limiter: Limiter):
    serialized = None
    limit = limiter.limit
    if limit:
        serialized = {
            'leftSeconds': limit.left_seconds,
            'temporaryUnavailable': limit.left_attempts == 0
        }
    return {
        limiter.type.value: serialized
    }


def get_limits(user: User):
    result: Dict[str, Any] = {}
    limiters = [
        ResendVerificationEmailLimiter(user),
        ResendVerificationSMSLimiter(user),
        ResendVerificationCallLimiter(user),
        UploadKYCDocumentLimiter(user),
    ]
    for limiter in limiters:
        result.update(
            serialize_limit(limiter)
        )
    return result
