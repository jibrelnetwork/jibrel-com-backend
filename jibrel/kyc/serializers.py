from typing import Any, Optional, Tuple, Union

import magic
import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.files import File
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


class ResidencyVisaValidator(BaseValidator):

    def validate(self, data):
        required_fields = ['residencyVisaNumber', 'residencyVisaDocument']

        personal_id_type = data.get('personalIdType')
        if personal_id_type != BasicKYCSubmission.PASSPORT:
            return

        if data.get('isResidencyVisaDoeHijri'):
            required_fields.append('residencyVisaDoeHijri')
        else:
            required_fields.append('residencyVisaDoe')

        for field in required_fields:
            if not data.get(field):
                self.add_error(field, 'required')


class PersonalIdTypeValidator(BaseValidator):
    default_error_messages = {'invalid': 'This value is not valid'}

    def validate(self, data):
        personal_id_type = data['personalIdType']
        citizenship = data['citizenship']
        residency = data['residency']
        if (citizenship not in BasicKYCSubmission.SUPPORTED_COUNTRIES
            and residency not in BasicKYCSubmission.SUPPORTED_COUNTRIES):
            self.add_error('citizenship', 'invalid')
            self.add_error('residency', 'invalid')
            self.raise_error()
        if citizenship in BasicKYCSubmission.SUPPORTED_COUNTRIES and citizenship != residency:
            self.add_error('residency', 'invalid')
            self.raise_error()
        if (citizenship in BasicKYCSubmission.SUPPORTED_COUNTRIES
            and personal_id_type == BasicKYCSubmission.NATIONAL_ID):
            return
        elif (residency in BasicKYCSubmission.SUPPORTED_COUNTRIES
              and personal_id_type == BasicKYCSubmission.PASSPORT):
            return
        self.add_error('personalIdType', 'invalid')


class PersonalIDValidator(BaseValidator):
    def validate(self, data):
        personal_id_type = data['personalIdType']
        if personal_id_type == BasicKYCSubmission.NATIONAL_ID:
            if not data.get('personalIdDocumentBack'):
                raise ValidationError([{
                    'personalIdDocumentBack': ErrorDetail(self.error_messages['required'], 'required')
                }])


class NestedFieldValidator:
    def __init__(self, field_name, value: Optional[Any] = None):
        self.field_name = field_name
        self.value = value

    def validate(self, data: dict) -> Union[Tuple[bool, dict], Tuple[bool, Tuple[str, str]]]:
        if not data.get(self.field_name):
            return False, ('required', 'This field is required111.')
        return True, data


class MinAgeValidator(NestedFieldValidator):
    def validate(
        self,
        data: dict
    ) -> Union[Tuple[bool, dict], Tuple[bool, Tuple[str, str]]]:
        date = data.get(self.field_name)
        if not date:
            return super().validate(data)
        today = timezone.now().date()
        if date > today - relativedelta(years=self.value):
            return False, ('invalid', f'You must be over {self.value} years old')
        return True, data


class DateDiffValidator(NestedFieldValidator):
    def validate(
        self,
        data: dict
    ) -> Union[Tuple[bool, dict], Tuple[bool, Tuple[str, str]]]:
        date = data.get(self.field_name)
        if not date:
            return super().validate(data)
        date = data.get(self.field_name)
        if (date - timezone.now().date()).days < self.value:
            return False, ('invalid', f'At least {self.value} must be remain from today')
        return True, data


class TernaryFieldValidator(BaseValidator):
    def __init__(
        self,
        condition_field: str,
        field_if_true: NestedFieldValidator,
        field_if_false: NestedFieldValidator
    ):
        super().__init__()
        self._condition_field = condition_field
        self._field_if_true = field_if_true
        self._field_if_false = field_if_false

    def validate(self, data):
        # no condition field -> field is not required, skip validation
        if data.get(self._condition_field) is None:
            return data

        validation_field = self._field_if_true
        empty_value_field = self._field_if_false
        if not data.get(self._condition_field):
            validation_field, empty_value_field = empty_value_field, validation_field

        data.pop(empty_value_field.field_name, None)
        is_ok, rest = validation_field.validate(data)
        if not is_ok:
            self.add_error(validation_field.field_name, *rest)
        return data


class BasicKYCSubmissionSerializer(serializers.Serializer):
    citizenship = CountryField()
    residency = CountryField()
    firstName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    middleName = serializers.CharField(
        max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')], default=''
    )
    lastName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    birthDate = serializers.DateField(required=False)
    birthDateHijri = serializers.CharField(max_length=32, required=False)
    personalIdType = serializers.ChoiceField(choices=BasicKYCSubmission.PERSONAL_ID_TYPES)
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
    residencyVisaNumber = serializers.CharField(max_length=20, required=False)
    residencyVisaDoe = serializers.DateField(required=False)
    residencyVisaDoeHijri = serializers.CharField(max_length=32, required=False)
    residencyVisaDocument = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.not_used_in_basic_kyc().filter(type=Document.RESIDENCY_VISA),
        required=False
    )
    isAgreedAMLPolicy = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    isBirthDateHijri = serializers.BooleanField()
    isConfirmedUBO = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    isPersonalIdDoeHijri = serializers.BooleanField()
    isResidencyVisaDoeHijri = serializers.NullBooleanField(required=False)

    class Meta:
        validators = [
            PersonalIdTypeValidator(),
            ResidencyVisaValidator(),
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
        TernaryFieldValidator(
            'isResidencyVisaDoeHijri',
            NestedFieldValidator('residencyVisaDoeHijri'),
            DateDiffValidator(
                'residencyVisaDoe',
                BasicKYCSubmission.MIN_DAYS_TO_EXPIRATION
            )
        )
    )
    depend_on_profile_related_fields = ('personalIdDocumentFront', 'personalIdDocumentBack', 'residencyVisaDocument')

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


class AddedKYCDocumentsSerializer(serializers.Serializer):
    type = serializers.CharField(source='type.value')
    doe = serializers.DateField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    last_name = serializers.CharField()
