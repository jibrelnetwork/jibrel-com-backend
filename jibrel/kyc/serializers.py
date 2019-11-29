from typing import Any, Optional, Tuple, Union

import magic
import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.files import File
from django.db import models
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError

from jibrel.authentication.models import Phone
from jibrel.core.errors import InvalidException
from jibrel.core.rest_framework import (
    AlwaysTrueFieldValidator,
    BaseValidator,
    CountryField,
    RegexValidator
)
from jibrel.kyc.models import BasicKYCSubmission, Document

from .validators import (
    PersonalIdTypeValidator,
    PersonalIDValidator,
    NestedFieldValidator,
    MinAgeValidator,
    DateDiffValidator,
    TernaryFieldValidator
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
        model = Document
        fields = (
            'file', 'type', 'side'
        )
        extra_kwargs = {
            'file': {'allow_empty_file': True}  # we have min size validation below, no need to validate zero especially
        }

    def validate_file(self, file: File) -> File:
        errors = []
        if (file.size < Document.MIN_SIZE) or (file.size > Document.MAX_SIZE):
            errors.append(
                ErrorDetail(
                    f'File size `{file.size}` should be in range from `{Document.MIN_SIZE}` to `{Document.MAX_SIZE}`',
                    'invalid'
                )
            )
        magic_bytes = file.read(1024)
        file.seek(0)
        mime_type = magic.from_buffer(magic_bytes, mime=True)
        if mime_type not in Document.SUPPORTED_MIME_TYPES:
            errors.append(
                ErrorDetail(
                    f'File type `{mime_type}` not supported',
                    'invalid'
                )
            )
        if errors:
            raise ValidationError(errors)
        return file


class PersonalKYCSubmissionSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    lastName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    middleName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
                                       required=False, default='')
    alias = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')], required=False)
    nationality = CountryField()
    birthDate = serializers.DateField(required=False)
    birthDateHijri = serializers.CharField(max_length=32, required=False)

    streetAddress = serializers.CharField(max_length=320)
    apartment = serializers.CharField(max_length=320)
    city = serializers.CharField(max_length=320)
    postCode = serializers.CharField(max_length=320)
    country = CountryField()

    occupation = serializers.CharField(max_length=320)
    incomeSource = serializers.CharField(max_length=320)

    personalIdType = serializers.ChoiceField(choices=Document.PERSONAL_ID_TYPES)
    personalIdNumber = serializers.CharField(max_length=20)
    personalIdDoe = serializers.DateField(required=False)
    personalIdDoeHijri = serializers.CharField(max_length=32, required=False)
    personalIdDocumentFront = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.not_used_in_basic_kyc().filter(
            Q(type=Document.NATIONAL_ID) | Q(type=Document.PASSPORT)
        )
    )
    personalIdDocumentBack = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.not_used_in_basic_kyc().filter(type=Document.NATIONAL_ID),
        required=False
    )
    proofOfAddress = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.not_used_in_basic_kyc().filter(type=Document.PROOF_OF_ADDRESS),
        required=False
    )
    amlAgreed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    uboConfirmed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    isBirthDateHijri = serializers.BooleanField()
    isPersonalIdDoeHijri = serializers.BooleanField()

    class Meta:
        validators = [
            PersonalIdTypeValidator(),
            PersonalIDValidator()
        ]

    additional_validators = (
        TernaryFieldValidator(
            'isBirthDateHijri',
            NestedFieldValidator('birthDateHijri'),
            MinAgeValidator(
                'birthDate',
                BasicKYCSubmission.MIN_AGE
            )
        ),
        TernaryFieldValidator(
            'isPersonalIdDoeHijri',
            NestedFieldValidator('personalIdDoeHijri'),
            DateDiffValidator(
                'personalIdDoe',
                BasicKYCSubmission.MIN_DAYS_TO_EXPIRATION
            )
        ),
    )
    depend_on_profile_related_fields = (
        'personalIdDocumentFront',
        'personalIdDocumentBack',
        'proofOfAddress'
    )

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        profile = self.context['profile']
        for field_name in self.depend_on_profile_related_fields:
            self.fields[field_name].queryset = self.fields[field_name].queryset.filter(profile=profile)

    def validate(self, data):
        for additional_validator in self.additional_validators:
            if hasattr(additional_validator, 'set_context'):
                additional_validator.set_context(self)
            additional_validator(data)
        return data


class BusinessKYCBeneficiarySerializer(serializers.Serializer):
    pass


class BusinessKYCSubmissionSerializer(serializers.Serializer):
    pass


class AddedKYCDocumentsSerializer(serializers.Serializer):
    type = serializers.CharField(source='type.value')
    doe = serializers.DateField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    last_name = serializers.CharField()
