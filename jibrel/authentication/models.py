from typing import Optional
from uuid import uuid4

import phonenumbers
import pycountry
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_banking.core.exceptions import NonSupportedCountryException
from django_banking.settings import SUPPORTED_COUNTRIES

from .managers import (
    ProfileManager,
    UserManager
)


class User(AbstractBaseUser):
    USERNAME_FIELD = 'email'

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    email = models.CharField(max_length=320, unique=True)
    is_email_confirmed = models.BooleanField(default=False)

    objects = UserManager()

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    admin_note = models.TextField(blank=True)

    NonSupportedCountryException = NonSupportedCountryException

    def get_residency_country_code(self) -> str:
        """Get financial residency of customer based on last approved kyc record if exists or based on phone number

        :return:
        """
        code = None
        profile = self.profile
        if profile.last_kyc is not None:
            code = profile.last_kyc.details.country or profile.last_kyc.details.nationality
        else:
            phone = profile.phone
            if phone is not None:
                region_code = phonenumbers.region_code_for_number(
                    phonenumbers.PhoneNumber(country_code=phone.code, national_number=phone.number)
                )
                country = pycountry.countries.get(alpha_2=region_code.upper())
                code = country and country.alpha_2
        if code:
            code = code.upper()
        if code not in SUPPORTED_COUNTRIES:
            raise NonSupportedCountryException('Country is not supported')
        return code

    def __str__(self):
        return self.email


class Profile(models.Model):
    KYC_PENDING = 'pending'
    KYC_UNVERIFIED = 'unverified'
    KYC_VERIFIED = 'verified'
    KYC_ADVANCED = 'advanced'

    KYC_STATUS_CHOICES = (
        (KYC_PENDING, 'Pending'),
        (KYC_UNVERIFIED, 'Unverified'),
        (KYC_VERIFIED, 'Verified'),
        (KYC_ADVANCED, 'Advanced verification'),
    )

    user = models.OneToOneField(to=User, on_delete=models.PROTECT)
    username = models.CharField(max_length=128)

    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    is_agreed_documents = models.BooleanField(default=False)

    kyc_status = models.CharField(choices=KYC_STATUS_CHOICES, default=KYC_UNVERIFIED, max_length=20)
    last_kyc = models.OneToOneField(
        to='kyc.BaseKYCSubmission', null=True, on_delete=models.SET_NULL, related_name='+'
    )

    language = models.CharField(max_length=2, blank=True)

    objects = ProfileManager()

    @property
    def phone(self) -> Optional['Phone']:
        return self.phones.order_by('created_at').last()

    @property
    def is_phone_confirmed(self) -> bool:
        return bool(self.phone and self.phone.is_confirmed)

    def __str__(self):
        return str(self.user.email)


class Phone(models.Model):
    UNCONFIRMED = 'unconfirmed'
    CODE_REQUESTED = 'code_requested'
    CODE_SENT = 'code_sent'
    CODE_SUBMITTED = 'code_submitted'
    CODE_INCORRECT = 'code_incorrect'
    EXPIRED = 'expired'
    MAX_ATTEMPTS_REACHED = 'max_attempts_reached'
    VERIFIED = 'verified'

    STATUS_CHOICES = (
        (UNCONFIRMED, 'Unconfirmed'),
        (CODE_REQUESTED, 'Code requested'),
        (CODE_SENT, 'Code sent'),
        (CODE_SUBMITTED, 'Code submitted'),
        (CODE_INCORRECT, 'Code incorrect'),
        (EXPIRED, 'Expired'),
        (MAX_ATTEMPTS_REACHED, 'Max attempts reached'),
        (VERIFIED, 'Verified'),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    profile = models.ForeignKey(to=Profile, related_name='phones', on_delete=models.PROTECT)

    number = models.CharField(max_length=32)

    status = models.CharField(max_length=320, choices=STATUS_CHOICES, default=UNCONFIRMED)

    code_requested_at = models.DateTimeField(null=True)
    code_submitted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_confirmed(self):
        return self.status == self.VERIFIED

    def set_code_requested(self):
        self.status = self.CODE_REQUESTED
        self.code_requested_at = timezone.now()
        self.save()

    def set_code_submitted(self):
        self.status = self.CODE_SUBMITTED
        self.code_submitted_at = timezone.now()
        self.save()


class OneTimeToken(models.Model):
    EMAIL_VERIFICATION = 1
    PASSWORD_RESET_ACTIVATE = 2
    PASSWORD_RESET_COMPLETE = 3
    CRYPTO_WITHDRAWAL_CONFIRMATION = 4

    OPERATION_TYPES = (
        (EMAIL_VERIFICATION, 'Email verification'),
        (PASSWORD_RESET_ACTIVATE, 'Password reset activate'),
        (PASSWORD_RESET_COMPLETE, 'Password reset'),
        (CRYPTO_WITHDRAWAL_CONFIRMATION, 'Crypto withdrawal confirmation'),
    )

    user = models.ForeignKey(to=User, on_delete=models.PROTECT)
    token = models.UUIDField(default=uuid4)
    checked = models.BooleanField(default=False)
    operation_type = models.IntegerField(choices=OPERATION_TYPES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.token)
