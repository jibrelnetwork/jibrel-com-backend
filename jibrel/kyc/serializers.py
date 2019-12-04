import magic
import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.files import File
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError

from jibrel.authentication.models import Phone
from jibrel.core.errors import InvalidException
from jibrel.core.rest_framework import (
    AlwaysTrueFieldValidator,
    CountryField,
    RegexValidator
)
from jibrel.kyc.constants import OCCUPATION_CHOICES, INCOME_SOURCE_CHOICES
from jibrel.kyc.models import (
    KYCDocument,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission,
    Director,
    OfficeAddress,
    Beneficiary,
)


class PhoneRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = (
            'code', 'number'
        )
        extra_kwargs = {
            'code': {'validators': [RegexValidator(r'[\d]+')]},
            'number': {'validators': [RegexValidator(r'[\d]+')]},
        }

    def validate(self, attrs):
        code = attrs['code']
        number = attrs['number']
        try:
            phone = phonenumbers.parse(f'+{code}{number}')
        except phonenumbers.NumberParseException as exc:
            raise InvalidException('number', message=str(exc))

        if not phonenumbers.is_valid_number(phone):
            raise InvalidException('number')

        return attrs


class VerifyPhoneRequestSerializer(serializers.Serializer):
    pin = serializers.CharField(max_length=6)


class UploadDocumentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = (
            'file', 'type', 'side'
        )
        extra_kwargs = {
            'file': {'allow_empty_file': True}  # we have min size validation below, no need to validate zero especially
        }

    def validate_file(self, file: File) -> File:
        errors = []
        if (file.size < KYCDocument.MIN_SIZE) or (file.size > KYCDocument.MAX_SIZE):
            errors.append(
                ErrorDetail(
                    f'File size `{file.size}` should be in range from ' +
                    f'`{KYCDocument.MIN_SIZE}` to `{KYCDocument.MAX_SIZE}`',
                    'invalid'
                )
            )
        magic_bytes = file.read(1024)
        file.seek(0)
        mime_type = magic.from_buffer(magic_bytes, mime=True)
        if mime_type not in KYCDocument.SUPPORTED_MIME_TYPES:
            errors.append(
                ErrorDetail(
                    f'File type `{mime_type}` not supported',
                    'invalid'
                )
            )
        if errors:
            raise ValidationError(errors)
        return file


def date_diff_validator(days):
    def _date_diff_validator(date):
        if (date - timezone.now().date()).days < days:
            raise ValidationError(f'At least {days} must be remain from today')
    return _date_diff_validator


def min_age_validator(age):
    def _min_age_validator(birth_date):
        today = timezone.now().date()
        if birth_date > today - relativedelta(years=age):
            raise ValidationError(f'You must be over {age} years old')
    return _min_age_validator


def validate_at_least_one_required(data_source, *fields):
    for field in fields:
        if data_source.get(field):
            return
    raise ValidationError({fields[0]: 'required'})


class AddressSerializerMixin(serializers.Serializer):
    streetAddress = serializers.CharField(max_length=320)
    apartment = serializers.CharField(
        max_length=320,
        required=False,
    )
    city = serializers.CharField(max_length=320)
    postCode = serializers.CharField(
        max_length=320,
        required=False,
    )
    country = CountryField()


class PersonNameSerializerMixin(serializers.Serializer):
    firstName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    lastName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    middleName = serializers.CharField(
        max_length=320,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        required=False,
    )


class BaseKYCSerializer(PersonNameSerializerMixin, AddressSerializerMixin, serializers.Serializer):

    nationality = CountryField()
    birthDate = serializers.DateField(validators=[min_age_validator(IndividualKYCSubmission.MIN_AGE)])
    email = serializers.EmailField(max_length=320)

    passportNumber = serializers.CharField(max_length=320)
    passportExpirationDate = serializers.DateField(
        validators=[date_diff_validator(IndividualKYCSubmission.MIN_DAYS_TO_EXPIRATION)]
    )
    passportDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )
    proofOfAddressDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )


class IndividualKYCSubmissionSerializer(BaseKYCSerializer):

    alias = serializers.CharField(
        max_length=320,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        required=False,
    )

    occupation = serializers.ChoiceField(
        choices=OCCUPATION_CHOICES,
        required=False,
    )
    occupationOther = serializers.CharField(
        max_length=320,
        required=False,
    )
    incomeSource = serializers.ChoiceField(
        choices=INCOME_SOURCE_CHOICES,
        required=False,
    )
    incomeSourceOther = serializers.CharField(
        max_length=320,
        required=False,
    )

    amlAgreed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    uboConfirmed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])

    depend_on_profile_related_fields = (
        'passportDocument',
        'proofOfAddressDocument'
    )

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        profile = self.context['profile']
        for field_name in self.depend_on_profile_related_fields:
            self.fields[field_name].queryset = self.fields[field_name].queryset.filter(profile=profile)

    def validate(self, data):
        validate_at_least_one_required(data, 'occupation', 'occupationOther')
        validate_at_least_one_required(data, 'incomeSource', 'incomeSourceOther')
        return data


class CompanyInfoSerializer(serializers.Serializer):
    companyName = serializers.CharField(
        max_length=320,
        required=False,
    )
    tradingName = serializers.CharField(
        max_length=320,
        required=False,
    )
    placeOfIncorporation = serializers.CharField(
        max_length=320,
        required=False,
    )
    dateOfIncorporation = serializers.DateField()
    commercialRegister = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )
    shareholderRegister = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )
    articlesOfIncorporation = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )


class OfficeAddresSerializer(AddressSerializerMixin, serializers.Serializer):
    pass


class DirectorSerializer(PersonNameSerializerMixin, serializers.Serializer):
    pass


class BenificiarySerializer(PersonNameSerializerMixin, AddressSerializerMixin, serializers.Serializer):
    nationality = CountryField()
    birthDate = serializers.DateField()
    email = serializers.EmailField(max_length=320)


class OrganisationalKYCSubmissionSerializer(BaseKYCSerializer):
    companyInfo = CompanyInfoSerializer(many=False)
    companyAddressRegistered = OfficeAddresSerializer(many=False)
    companyAddressPrincipal = OfficeAddresSerializer(many=False)
    beneficiaries = BenificiarySerializer(many=True)
    directors = DirectorSerializer(many=True)

    def create(self, validated_data):
        return OrganisationalKYCSubmission.objects.create(**validated_data)
