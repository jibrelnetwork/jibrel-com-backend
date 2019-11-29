from typing import Any, Optional, Tuple, Union

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework.exceptions import ErrorDetail, ValidationError

from jibrel.core.rest_framework import (
    BaseValidator,
)
from jibrel.kyc.models import (
    BasicKYCSubmission,
    Document
)


class PersonalIdTypeValidator(BaseValidator):
    default_error_messages = {'invalid': 'This value is not valid'}

    def validate(self, data):
        personal_id_type = data['personalIdType']
        citizenship = data['country']
        residency = data['nationality']
        if (citizenship not in BasicKYCSubmission.SUPPORTED_COUNTRIES
            and residency not in BasicKYCSubmission.SUPPORTED_COUNTRIES):
            self.add_error('country', 'invalid')
            self.add_error('nationality', 'invalid')
            self.raise_error()
        if citizenship in BasicKYCSubmission.SUPPORTED_COUNTRIES and citizenship != residency:
            self.add_error('country', 'invalid')
            self.raise_error()
        if (citizenship in BasicKYCSubmission.SUPPORTED_COUNTRIES
            and personal_id_type == Document.NATIONAL_ID):
            return
        elif (residency in BasicKYCSubmission.SUPPORTED_COUNTRIES
              and personal_id_type == Document.PASSPORT):
            return
        self.add_error('personalIdType', 'invalid')


class PersonalIDValidator(BaseValidator):
    def validate(self, data):
        personal_id_type = data['personalIdType']
        if personal_id_type == Document.NATIONAL_ID:
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


class InArrayValidator(BaseValidator):
    def __init__(
        self,
        values_list: list,
    ):
        super().__init__()
        self.values_list = values_list

    def validate(self, data):
        if data not in self.values_list:
            return False, 'Bad value'
        return True, data
