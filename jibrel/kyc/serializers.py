import magic
import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError

from jibrel.authentication.models import Phone
from jibrel.core.errors import ErrorCode
from jibrel.core.rest_framework import (
    AlwaysTrueFieldValidator,
    CountryField,
    RegexValidator
)
from jibrel.core.serializers import PhoneNumberField
from jibrel.kyc.constants import INCOME_SOURCE_CHOICES, OCCUPATION_CHOICES
from jibrel.kyc.models import (
    IndividualKYCSubmission,
    KYCDocument,
    OfficeAddress,
    OrganisationalKYCSubmission
)


class PhoneSerializer(serializers.ModelSerializer):
    number = PhoneNumberField()

    class Meta:
        model = Phone
        fields = (
            'number',
            'status',
        )
        extra_kwargs = {
            'status': {'read_only': True},
        }

    def validate_number(self, number: str):
        if self.instance is not None and self.instance.number == number:
            raise ValidationError('Submitted same number', code=ErrorCode.SAME)
        return number


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
    streetAddress = serializers.CharField(max_length=320, source='street_address')
    apartment = serializers.CharField(
        max_length=320,
        required=False,
    )
    city = serializers.CharField(max_length=320)
    postCode = serializers.CharField(
        max_length=320,
        required=False,
        source='post_code',
    )
    country = CountryField()


class PersonNameSerializerMixin(serializers.Serializer):
    firstName = serializers.CharField(
        max_length=30,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        source='first_name'
    )
    lastName = serializers.CharField(
        max_length=30,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        source='last_name'
    )
    middleName = serializers.CharField(
        max_length=30,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        required=False,
        source='middle_name'
    )


class BaseKYCSerializer(PersonNameSerializerMixin, AddressSerializerMixin, serializers.Serializer):
    nationality = CountryField()
    birthDate = serializers.DateField(validators=[min_age_validator(IndividualKYCSubmission.MIN_AGE)],
                                      source='birth_date')

    passportNumber = serializers.CharField(max_length=320, source='passport_number')
    passportExpirationDate = serializers.DateField(
        validators=[date_diff_validator(IndividualKYCSubmission.MIN_DAYS_TO_EXPIRATION)],
        source='passport_expiration_date',
    )
    passportDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc(),
        source='passport_document',
    )
    proofOfAddressDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc(),
        source='proof_of_address_document',
    )


class IndividualKYCSubmissionSerializer(BaseKYCSerializer):
    alias = serializers.CharField(
        max_length=30,
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


class OfficeAddresSerializer(AddressSerializerMixin, serializers.Serializer):
    pass


class DirectorSerializer(serializers.Serializer):
    fullName = serializers.CharField(
        max_length=50,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        source='full_name'
    )


class BenificiarySerializer(AddressSerializerMixin, serializers.Serializer):
    fullName = serializers.CharField(
        max_length=50,
        validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
        source='full_name'
    )
    phoneNumber = serializers.CharField(
        max_length=320,
        source='phone_number'
    )
    nationality = CountryField()
    birthDate = serializers.DateField(source='birth_date')
    email = serializers.EmailField(max_length=320)

    def validate_phoneNumber(self, value):
        try:
            parsed_number = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError("Invalid phone number format: {}".format(value))
        if phonenumbers.is_valid_number(parsed_number) is False:
            raise serializers.ValidationError("Invalid phone number format: {}".format(value))
        return value


class OrganisationalKYCSubmissionSerializer(BaseKYCSerializer):
    email = serializers.EmailField(max_length=320)
    phoneNumber = serializers.CharField(
        max_length=320,
        source='phone_number'
    )
    companyAddressRegistered = OfficeAddresSerializer(many=False)
    companyAddressPrincipal = OfficeAddresSerializer(many=False, required=False)
    beneficiaries = BenificiarySerializer(many=True, required=True, allow_empty=False)
    directors = DirectorSerializer(many=True, required=True, allow_empty=False)

    companyName = serializers.CharField(
        max_length=30,
        source='company_name',
    )
    tradingName = serializers.CharField(
        max_length=30,
        source='trading_name',
    )
    placeOfIncorporation = serializers.CharField(
        max_length=320,
        source='place_of_incorporation',
    )
    dateOfIncorporation = serializers.DateField(source='date_of_incorporation')
    commercialRegister = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc(),
        source='commercial_register',
    )
    shareholderRegister = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc(),
        source='shareholder_register',
    )
    articlesOfIncorporation = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc(),
        source='articles_of_incorporation',
    )

    def validate_phoneNumber(self, value):
        try:
            parsed_number = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError("Invalid phone number format: {}".format(value))
        if phonenumbers.is_valid_number(parsed_number) is False:
            raise serializers.ValidationError("Invalid phone number format: {}".format(value))
        return value

    @transaction.atomic
    def create(self, validated_data):
        beneficiaries_data = validated_data.pop('beneficiaries')
        directors_data = validated_data.pop('directors')
        address_registered_data = validated_data.pop('companyAddressRegistered')
        try:
            address_principal_data = validated_data.pop('companyAddressPrincipal')
        except KeyError:
            address_principal_data = None

        submission = OrganisationalKYCSubmission.objects.create(**validated_data)
        OfficeAddress.objects.create(kyc_registered_here=submission, **address_registered_data)
        if address_principal_data:
            OfficeAddress.objects.create(kyc_principal_here=submission, **address_principal_data)

        for item in beneficiaries_data:
            submission.beneficiaries.create(**item)
        for item in directors_data:
            submission.directors.create(**item)

        return submission
