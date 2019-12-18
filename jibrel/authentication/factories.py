import factory
from django.utils import timezone

from ..kyc.models import (
    IndividualKYCSubmission,
    KYCDocument
)
from .models import (
    Phone,
    Profile,
    User
)


class KYCDocumentFactory(factory.DjangoModelFactory):
    class Meta:
        model = KYCDocument


class ApprovedKYCFactory(factory.DjangoModelFactory):
    status = IndividualKYCSubmission.APPROVED
    transitioned_at = factory.Faker('date_time', tzinfo=timezone.get_current_timezone())
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    birth_date = factory.Faker('date_object')
    nationality = 'ae'
    street_address = factory.Faker('address')
    city = factory.Faker('city')
    country = 'ae'
    occupation_other = 'some'
    income_source_other = 'some'
    passport_number = '1'
    passport_expiration_date = factory.Faker('date_object')
    passport_document = factory.SubFactory(KYCDocumentFactory)
    proof_of_address_document = factory.SubFactory(KYCDocumentFactory)
    aml_agreed = True
    ubo_confirmed = True

    class Meta:
        model = IndividualKYCSubmission


class ApprovedPhoneFactory(factory.DjangoModelFactory):
    number = factory.Faker('msisdn')
    status = Phone.VERIFIED

    class Meta:
        model = Phone


class ProfileFactory(factory.DjangoModelFactory):
    kyc_status = Profile.KYC_VERIFIED
    language = 'ar'
    is_agreed_terms = True
    is_agreed_privacy_policy = True
    phone = factory.RelatedFactory(ApprovedPhoneFactory, 'profile')

    class Meta:
        model = Profile

    @factory.post_generation
    def verified(self, create, extracted, **kwargs):
        if extracted:
            ApprovedKYCFactory.create(
                profile=self,
                passport_document__profile=self,
                proof_of_address_document__profile=self,
            )


class VerifiedUser(factory.DjangoModelFactory):
    email = factory.Faker('email')
    is_email_confirmed = True
    profile = factory.RelatedFactory(ProfileFactory, 'user', verified=True)

    class Meta:
        model = User
