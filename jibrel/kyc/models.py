import datetime
import enum
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.contrib.postgres.fields import (
    ArrayField,
    JSONField
)


from jibrel.authentication.models import Profile
from jibrel.core.common.json import LazyEncoder
from jibrel.core.storages import kyc_file_storage

from .exceptions import BadTransitionError
from .managers import BasicKYCSubmissionManager
from .queryset import DocumentQuerySet, PhoneVerificationQuerySet


class PhoneVerification(models.Model):
    """Model represents and persists verification submission

    Notes
        verification_sid correlates with Twilio APIv2
        task_ids correlates with celery task id and ExternalServiceCallLog uuid

    Attributes
        verification_sid: identifier of verification
        phone: authentication.Phone instance which should be validated
        status: value of VerificationStatus
        task_ids: unique identifiers of requests to validate phone
        created_at: datetime of record creation
    """

    PENDING = 'pending'  # Verification created, no valid code has been checked
    APPROVED = 'approved'  # Verification approved, the checked code was valid
    EXPIRED = 'expired'  # The verification was not approved within the valid timeline
    MAX_ATTEMPTS_REACHED = 'max_attempts_reached'  # The user has attempted to verify an invalid code more than 5 times
    CANCELED = 'canceled'  # The verification was canceled by the customer

    VERIFICATION_STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (EXPIRED, 'Expired'),
        (MAX_ATTEMPTS_REACHED, 'Max attempts reached'),
        (CANCELED, 'Canceled'),
    )

    verification_sid = models.CharField(max_length=255, primary_key=True)
    phone = models.ForeignKey(to='authentication.Phone', on_delete=models.PROTECT, related_name='verification_requests')
    status = models.CharField(choices=VERIFICATION_STATUS_CHOICES, max_length=1200)

    task_ids = ArrayField(models.UUIDField(), default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = PhoneVerificationQuerySet.as_manager()

    @classmethod
    def submit(
        cls,
        sid: str,
        phone_id: uuid.UUID,
        task_id: uuid.UUID,
        status: str
    ) -> 'PhoneVerification':
        """Submit new verification attempt

        If verification with `sid` was created previously we just update its status and store task_id

        Args:
            sid:
            phone_id:
            task_id:
            status:

        Returns:
            created or updated verification instance
        """
        verification, _ = cls.objects.update_or_create(
            verification_sid=sid,
            phone_id=phone_id,
            defaults={
                'status': status
            }
        )
        verification.task_ids.append(task_id)
        verification.save()
        return verification


class PhoneVerificationCheck(models.Model):
    """Model represents and persists attempt to check verification

    Notes
        task_id correlates with celery task id and ExternalServiceCallLog uuid

    Attributes
        verification: verification instance is attempted to check
        task_id: unique identifier of request to check validation
        failed: flag tells any error raised in check attempt
        created_at: datetime of record creation
    """

    verification = models.ForeignKey(to=PhoneVerification, on_delete=models.PROTECT, related_name='checks')

    task_id = models.UUIDField()
    failed = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    SUPPORTED_MIME_TYPES = (
        'image/jpeg',
        'image/pjpeg',
        'image/png',
        'application/pdf',
    )

    MAX_SIZE = 10 * 1024 * 1024
    MIN_SIZE = 32 * 1024

    PASSPORT = 'passport'
    NATIONAL_ID = 'national_id'
    PROOF_OF_ADDRESS = 'proof_of_address'
    PERSONAL_ID_TYPES = (
        (PASSPORT, 'Passport'),
        (NATIONAL_ID, 'National ID'),
        (PROOF_OF_ADDRESS, 'Proof of address'),
    )
    DOCUMENT_TYPES = list(PERSONAL_ID_TYPES)

    FRONT_SIDE = 'front'
    BACK_SIDE = 'back'
    SIDES = (
        (FRONT_SIDE, 'Front side'),
        (BACK_SIDE, 'Back side'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    file = models.FileField(storage=kyc_file_storage)
    checksum = models.CharField(max_length=32)
    type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    side = models.CharField(max_length=20, choices=SIDES)
    created_at = models.DateTimeField(auto_now_add=True)

    profile = models.ForeignKey(to='authentication.Profile', on_delete=models.PROTECT)

    objects = DocumentQuerySet.as_manager()


class BasicKYCSubmission(models.Model):
    MIN_AGE = 21
    MIN_DAYS_TO_EXPIRATION = 31

    SUPPORTED_COUNTRIES = settings.SUPPORTED_COUNTRIES

    DRAFT = 'draft'
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = (
        (DRAFT, 'Draft'),
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    )

    PERSONAL = 'personal'
    BUSINESS = 'business'
    ACCOUNT_TYPES = (
        (PERSONAL, 'Personal'),
        (BUSINESS, 'Business'),
    )

    ONFIDO_RESULT_CLEAR = 'clear'
    ONFIDO_RESULT_CONSIDER = 'consider'
    ONFIDO_RESULT_CHOICES = (
        (ONFIDO_RESULT_CONSIDER, 'Consider'),
        (ONFIDO_RESULT_CLEAR, 'Clear'),
    )

    profile = models.ForeignKey(to='authentication.Profile', on_delete=models.PROTECT)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default=PERSONAL)
    schema = models.CharField(max_length=32, verbose_name='schema version')
    data = JSONField(encoder=LazyEncoder)

    admin_note = models.TextField(blank=True)
    reject_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    transitioned_at = models.DateTimeField()

    onfido_applicant_id = models.CharField(max_length=100, null=True, blank=True)
    onfido_check_id = models.CharField(max_length=100, null=True, blank=True)
    onfido_result = models.CharField(max_length=100, choices=ONFIDO_RESULT_CHOICES, null=True, blank=True)
    onfido_report = models.FileField(storage=kyc_file_storage, null=True)

    objects = BasicKYCSubmissionManager()

    def __str__(self) -> str:
        first_name = self.data['firstName']
        last_name = self.data['lastName']
        return f'Basic submission ({first_name[:1]}. {last_name}, {self.profile.user.email})'

    def is_approved(self):
        return self.status == self.APPROVED

    def is_rejected(self):
        return self.status == self.REJECTED

    @transaction.atomic()
    def approve(self) -> None:
        self.check_transition()
        self.profile.last_basic_kyc = self
        self.change_transition(self.APPROVED, Profile.KYC_VERIFIED)

    @transaction.atomic()
    def reject(self) -> None:
        self.check_transition()
        previous_approved = self._meta.model.objects.filter(
            profile=self.profile,
            status=self.APPROVED,
        ).exclude(
            pk=self.pk
        ).order_by('-transitioned_at').first()
        self.profile.last_basic_kyc = previous_approved
        self.change_transition(self.REJECTED, Profile.KYC_UNVERIFIED)

    def country(self):
        if self.account_type == self.PERSONAL:
            return self.data['country']
        else:
            return self.data['country']

    def clone(self) -> 'BasicKYCSubmission':
        self.pk = None
        self.status = self.DRAFT
        self.transitioned_at = timezone.now()
        self.created_at = timezone.now()
        self.save(using=settings.MAIN_DB_NAME)
        return self

    def check_transition(self):
        if not self._meta.model.objects.approved_later_exists(self):
            raise BadTransitionError

    def change_transition(self, status: str, profile_kyc_status: str) -> None:
        # TODO send mail
        self.status = status
        self.transitioned_at = timezone.now()
        self.save(using=settings.MAIN_DB_NAME)
        self.profile.kyc_status = profile_kyc_status
        self.profile.save(using=settings.MAIN_DB_NAME)


class PersonalDocumentType(enum.Enum):
    NATIONAL_ID: str = 'national_id'
    PASSPORT: str = 'passport'


@dataclass
class PersonalDocument:
    type: PersonalDocumentType
    doe: datetime.date
    first_name: str
    middle_name: str
    last_name: str
