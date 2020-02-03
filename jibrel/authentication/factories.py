import factory
from django.utils import timezone

from ..kyc.models import (
    Beneficiary,
    Director,
    IndividualKYCSubmission,
    KYCDocument,
    OfficeAddress,
    OrganisationalKYCSubmission
)
from .models import (
    Phone,
    Profile,
    User
)


class KYCDocumentFactory(factory.DjangoModelFactory):
    class Meta:
        model = KYCDocument


class KYCDocumentFactoryWithFileField(factory.DjangoModelFactory):
    class Meta:
        model = KYCDocument

    file = factory.django.FileField(filename='the_file.dat')


class OfficeAddressFactory(factory.DjangoModelFactory):
    street_address = factory.Faker('address')
    city = factory.Faker('city')
    country = 'ae'

    class Meta:
        model = OfficeAddress


class ApprovedIndividualKYCFactory(factory.DjangoModelFactory):
    status = IndividualKYCSubmission.APPROVED
    transitioned_at = factory.Faker('date_time', tzinfo=timezone.get_current_timezone())
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    birth_date = factory.Faker('date_object')
    nationality = 'ae'
    street_address = factory.Faker('address')
    city = factory.Faker('city')
    country = 'ae'
    occupation = 'other'
    income_source = 'other'
    passport_number = '1'
    passport_expiration_date = factory.Faker('date_object')
    passport_document = factory.SubFactory(KYCDocumentFactory)
    proof_of_address_document = factory.SubFactory(KYCDocumentFactory)

    @factory.post_generation
    def verified(self, create, extracted, **kwargs):
        if extracted:
            self.profile.last_kyc = self
            self.profile.save()

    class Meta:
        model = IndividualKYCSubmission


class ApprovedOrganisationalKYCFactory(factory.DjangoModelFactory):
    status = OrganisationalKYCSubmission.APPROVED
    transitioned_at = factory.Faker('date_time', tzinfo=timezone.get_current_timezone())
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    birth_date = factory.Faker('date_object')
    nationality = 'ae'
    email = factory.Faker('email')

    street_address = factory.Faker('address')
    city = factory.Faker('city')
    country = 'ae'

    passport_number = '1'
    passport_expiration_date = factory.Faker('date_object')
    passport_document = factory.SubFactory(KYCDocumentFactory)
    proof_of_address_document = factory.SubFactory(KYCDocumentFactory)
    phone_number = factory.Faker('phone_number')

    company_name = 'company_name'
    trading_name = 'trading_name'
    date_of_incorporation = factory.Faker('date_object')
    place_of_incorporation = factory.Faker('city')

    commercial_register = factory.SubFactory(KYCDocumentFactory)
    shareholder_register = factory.SubFactory(KYCDocumentFactory)
    articles_of_incorporation = factory.SubFactory(KYCDocumentFactory)

    @factory.post_generation
    def verified(self, create, extracted, **kwargs):
        self.profile.last_kyc = self
        OfficeAddressFactory.create(kyc_registered_here=self)
        OfficeAddressFactory.create(kyc_principal_here=self)
        DirectorFactory.create(organisational_submission=self)
        BeneficiaryFactory.create(
            organisational_submission=self,
            passport_document__profile=self.profile,
            proof_of_address_document__profile=self.profile,
        )
        self.profile.save()

    class Meta:
        model = OrganisationalKYCSubmission


class DirectorFactory(factory.DjangoModelFactory):
    full_name = factory.Faker('first_name')
    organisational_submission = factory.SubFactory(ApprovedOrganisationalKYCFactory)

    class Meta:
        model = Director


class BeneficiaryFactory(factory.DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    birth_date = factory.Faker('date_object')
    nationality = 'ae'
    phone_number = factory.Faker('phone_number')
    email = factory.Faker('email')
    passport_number = '1'
    passport_expiration_date = factory.Faker('date_object')

    passport_document = factory.SubFactory(KYCDocumentFactory)
    proof_of_address_document = factory.SubFactory(KYCDocumentFactory)
    organisational_submission = factory.SubFactory(ApprovedOrganisationalKYCFactory)

    class Meta:
        model = Beneficiary


class ApprovedPhoneFactory(factory.DjangoModelFactory):
    number = factory.Faker('msisdn')
    status = Phone.VERIFIED
    is_primary = True

    class Meta:
        model = Phone


class ProfileFactory(factory.DjangoModelFactory):
    kyc_status = Profile.KYC_VERIFIED
    language = 'ar'
    is_agreed_documents = True
    phone = factory.RelatedFactory(ApprovedPhoneFactory, 'profile')

    class Meta:
        model = Profile

    @factory.post_generation
    def verified(self, create, extracted, **kwargs):
        if extracted:
            ApprovedIndividualKYCFactory.create(
                profile=self,
                passport_document__profile=self,
                proof_of_address_document__profile=self,
                verified=True
            )

    @factory.post_generation
    def verified_organizational(self, create, extracted, **kwargs):
        if extracted:
            ApprovedOrganisationalKYCFactory.create(
                profile=self,
                passport_document__profile=self,
                commercial_register__profile=self,
                shareholder_register__profile=self,
                proof_of_address_document__profile=self,
                articles_of_incorporation__profile=self,
            )


class VerifiedUser(factory.DjangoModelFactory):
    email = factory.Faker('email')
    is_email_confirmed = True
    profile = factory.RelatedFactory(ProfileFactory, 'user', verified=True)

    class Meta:
        model = User


class VerifiedOrganisationalUser(factory.DjangoModelFactory):
    email = factory.Faker('email')
    is_email_confirmed = True
    profile = factory.RelatedFactory(ProfileFactory, 'user', verified_organizational=True)

    class Meta:
        model = User
