import uuid
from typing import Union

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.utils import timezone

from jibrel.authentication.models import Profile
from jibrel.core.storages import kyc_file_storage
from jibrel.kyc import constants

from .managers import IndividualKYCSubmissionManager
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


class KYCDocument(models.Model):
    SUPPORTED_MIME_TYPES = (
        'image/jpeg',
        'image/pjpeg',
        'image/png',
        'application/pdf',
    )

    MAX_SIZE = 10 * 1024 * 1024
    MIN_SIZE = 32 * 1024

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    file = models.FileField(storage=kyc_file_storage)
    checksum = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    profile = models.ForeignKey(to='authentication.Profile', on_delete=models.PROTECT)

    objects = DocumentQuerySet.as_manager()


class AddressMixing(models.Model):
    """
    Company Address
    """
    street_address = models.CharField(max_length=320)
    apartment = models.CharField(max_length=320, blank=True)
    post_code = models.CharField(max_length=320, blank=True)
    city = models.CharField(max_length=320)
    country = models.CharField(max_length=320)

    class Meta:
        abstract = True


class BaseKYCSubmission(AddressMixing, models.Model):
    MIN_AGE = 21
    MIN_DAYS_TO_EXPIRATION = 31

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

    INDIVIDUAL = 'individual'
    BUSINESS = 'business'
    ACCOUNT_TYPES = (
        (INDIVIDUAL, 'Individual'),
        (BUSINESS, 'Business'),
    )

    ONFIDO_RESULT_CLEAR = 'clear'
    ONFIDO_RESULT_CONSIDER = 'consider'
    ONFIDO_RESULT_CHOICES = (
        (ONFIDO_RESULT_CONSIDER, 'Consider'),
        (ONFIDO_RESULT_CLEAR, 'Clear'),
    )

    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)

    first_name = models.CharField(max_length=320)
    middle_name = models.CharField(max_length=320, blank=True)
    last_name = models.CharField(max_length=320)
    birth_date = models.DateField()
    nationality = models.CharField(max_length=2)
    email = models.EmailField()

    passport_number = models.CharField(max_length=320)
    passport_expiration_date = models.DateField()
    passport_document = models.ForeignKey(KYCDocument, on_delete=models.PROTECT, related_name='+')
    proof_of_address_document = models.ForeignKey(KYCDocument, on_delete=models.PROTECT, related_name='+')

    admin_note = models.TextField(blank=True)
    reject_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    transitioned_at = models.DateTimeField(auto_now_add=True)

    onfido_applicant_id = models.CharField(max_length=100, null=True, blank=True)
    onfido_check_id = models.CharField(max_length=100, null=True, blank=True)
    onfido_result = models.CharField(max_length=100, choices=ONFIDO_RESULT_CHOICES, null=True, blank=True)
    onfido_report = models.FileField(storage=kyc_file_storage, null=True)

    class Meta:
        abstract = True

    def is_approved(self):
        return self.status == self.APPROVED

    def is_rejected(self):
        return self.status == self.REJECTED

    @transaction.atomic()
    def approve(self) -> None:
        self.change_transition(self.APPROVED, Profile.KYC_VERIFIED)

    @transaction.atomic()
    def reject(self) -> None:
        self.change_transition(self.REJECTED, Profile.KYC_UNVERIFIED)

    def change_transition(self, status: str, profile_kyc_status: str) -> None:
        # TODO send mail
        self.status = status
        self.transitioned_at = timezone.now()
        self.save(using=settings.MAIN_DB_NAME)
        self.profile.kyc_status = profile_kyc_status
        self.profile.save(using=settings.MAIN_DB_NAME)

    @classmethod
    def get_submission(cls, account_type: str, pk: int) -> Union['IndividualKYCSubmission']:
        assert account_type in (cls.INDIVIDUAL, cls.BUSINESS)
        if account_type == cls.INDIVIDUAL:
            return IndividualKYCSubmission.objects.get(pk=pk)
        # todo
        raise ValueError


class IndividualKYCSubmission(BaseKYCSubmission):
    profile = models.ForeignKey(to='authentication.Profile', on_delete=models.PROTECT)

    occupation = models.CharField(choices=constants.OCCUPATION_CHOICES, max_length=320, blank=True)
    occupation_other = models.CharField(max_length=320, blank=True)
    income_source = models.CharField(choices=constants.INCOME_SOURCE_CHOICES, max_length=320, blank=True)
    income_source_other = models.CharField(max_length=320, blank=True)

    aml_agreed = models.BooleanField()
    ubo_confirmed = models.BooleanField()

    objects = IndividualKYCSubmissionManager()


class CompanyInfo(models.Model):
    """
    Organisational Investor KYC
    Company Information Data
    """
    company_name = models.CharField(max_length=320)
    trading_name = models.CharField(max_length=320)
    date_of_incorporation = models.DateField()
    place_of_incorporation = models.CharField(max_length=320)

    commercial_register = models.ForeignKey(KYCDocument, on_delete=models.PROTECT, related_name='+')
    shareholder_register = models.ForeignKey(KYCDocument, on_delete=models.PROTECT, related_name='+')
    articles_of_incorporation = models.ForeignKey(KYCDocument, on_delete=models.PROTECT, related_name='+')


class OfficeAddress(AddressMixing):
    pass


class PersonNameMixin(models.Model):
    full_name = models.CharField(max_length=320)

    class Meta:
        abstract = True


class OrganisationalKYCSubmission(BaseKYCSubmission):
    """
    Organisational Investor KYC
    Submission Data
    """
    profile = models.ForeignKey(to='authentication.Profile', on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=320)
    company_info = models.OneToOneField(
        CompanyInfo,
        on_delete=models.CASCADE,
    )
    company_address_registered = models.OneToOneField(
        OfficeAddress,
        on_delete=models.CASCADE,
        related_name='+',
    )
    company_address_principal = models.OneToOneField(
        OfficeAddress,
        on_delete=models.CASCADE,
        related_name='+',
        blank=True,
        null=True,
    )


class Beneficiary(PersonNameMixin, AddressMixing, models.Model):  # type: ignore
    birth_date = models.DateField()
    nationality = models.CharField(max_length=320)
    phone_number = models.CharField(max_length=320)
    email = models.EmailField()
    organisational_submission = models.ForeignKey(OrganisationalKYCSubmission,
                                                  on_delete=models.CASCADE,
                                                  related_name='beneficiaries')


class Director(PersonNameMixin):
    organisational_submission = models.ForeignKey(OrganisationalKYCSubmission,
                                                  on_delete=models.CASCADE,
                                                  related_name='directors')
