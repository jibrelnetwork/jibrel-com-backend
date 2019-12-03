import factory
from django.utils import timezone

from ..kyc.models import BasicKYCSubmission, Document
from .models import Phone, Profile, User


class KYCDocumentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Document


class ApprovedKYCFactory(factory.DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    status = BasicKYCSubmission.APPROVED
    birth_date = factory.Faker('date_object')
    personal_id_doe = factory.Faker('date_object')
    is_agreed_aml_policy = True
    is_confirmed_ubo = True
    transitioned_at = factory.Faker('date_time', tzinfo=timezone.get_current_timezone())
    personal_id_document_front = factory.SubFactory(KYCDocumentFactory)
    personal_id_document_back = factory.SubFactory(KYCDocumentFactory)
    citizenship = 'ae'
    residency = 'ae'

    class Meta:
        model = BasicKYCSubmission


class ApprovedPhoneFactory(factory.DjangoModelFactory):
    code = factory.Faker('pyint', min_value=1, max_value=99)
    number = factory.Faker('msisdn')
    is_confirmed = True

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
            self.last_basic_kyc = ApprovedKYCFactory.create(
                profile=self,
                personal_id_document_front__profile=self,
                personal_id_document_back__profile=self,
            )
            self.save()


class VerifiedUser(factory.DjangoModelFactory):
    email = factory.Faker('email')
    is_email_confirmed = True
    profile = factory.RelatedFactory(ProfileFactory, 'user', verified=True)

    class Meta:
        model = User
