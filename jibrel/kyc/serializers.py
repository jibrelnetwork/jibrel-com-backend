from typing import Any, Optional, Tuple, Union

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
    BaseValidator,
    CountryField,
    RegexValidator
)
from jibrel.kyc.constants import OCCUPATION_CHOICES, INCOME_SOURCE_CHOICES
from jibrel.kyc.models import KYCDocument


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


class IndividualKYCSubmissionSerializer(serializers.Serializer):
    firstName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    lastName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')])
    middleName = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')],
                                       required=False, default='')
    alias = serializers.CharField(max_length=320, validators=[RegexValidator(r'([^\W\d]|[\s-])+')], required=False)
    nationality = CountryField()
    birthDate = serializers.DateField(required=False)
    email = serializers.EmailField(max_length=320)

    streetAddress = serializers.CharField(max_length=320)
    unit = serializers.CharField(max_length=320, required=False)
    city = serializers.CharField(max_length=320)
    postCode = serializers.CharField(max_length=320, required=False)
    country = CountryField()

    occupation = serializers.ChoiceField(choices=OCCUPATION_CHOICES, required=False)
    occupationOther = serializers.CharField(max_length=320, required=False)
    incomeSource = serializers.ChoiceField(choices=INCOME_SOURCE_CHOICES, required=False)
    incomeSourceOther = serializers.CharField(max_length=320, required=False)

    passportNumber = serializers.CharField(max_length=320)
    passportExpirationDate = serializers.DateField()
    passportDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )
    proofOfAddressDocument = serializers.PrimaryKeyRelatedField(
        queryset=KYCDocument.objects.not_used_in_kyc()
    )

    amlAgreed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])
    uboConfirmed = serializers.BooleanField(validators=[AlwaysTrueFieldValidator()])

    additional_validators = (
        TernaryFieldValidator(
            'occupation',
            NestedFieldValidator('occupation'),
            NestedFieldValidator('occupationOther'),
        ),
        TernaryFieldValidator(
            'incomeSource',
            NestedFieldValidator('incomeSource'),
            NestedFieldValidator('incomeSourceOther'),
        ),
    )
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
        for additional_validator in self.additional_validators:
            if hasattr(additional_validator, 'set_context'):
                additional_validator.set_context(self)
            additional_validator(data)
        return data

