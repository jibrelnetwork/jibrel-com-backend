import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

import pycountry
from django.http import JsonResponse
from django.utils.encoding import smart_text
from rest_framework import serializers
from rest_framework.exceptions import (
    APIException,
    ErrorDetail,
    ValidationError
)
from rest_framework.views import exception_handler as drf_exception_handler

from jibrel.core.errors import CoinMENAException, Error, ErrorCode

drf_code_map = {
    'invalid': ErrorCode.INVALID,
    'required': ErrorCode.REQUIRED,
    'max_length': ErrorCode.TOO_LONG,
    'null': ErrorCode.NOT_NULL,
    'blank': ErrorCode.REQUIRED,
    'invalid_choice': ErrorCode.INVALID,
    'empty': ErrorCode.REQUIRED,
    'does_not_exist': ErrorCode.INVALID,
    'max_decimal_places': ErrorCode.INVALID,
    'max_digits': ErrorCode.INVALID,
}


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    serialized = serialize_exception(exc)
    if serialized:  # keep default DRF behavior if can't serialize errors
        response.data = {'errors': serialized}
    return response


def serialize_exception(exc: APIException) -> Optional[List[dict]]:
    if isinstance(getattr(exc, 'detail', None), (list, dict)):
        return get_serialized_errors(exc.detail)
    if isinstance(getattr(exc, 'detail', None), ErrorDetail):
        return [{'message': exc.detail}]
    return None


def get_serialized_errors(detail, field_name=None):
    """Convert DRF error to serialized core.errors.Error

    :param detail:
    :param field_name:
    :return:
    """

    errors = []
    if isinstance(detail, list):
        serialized = (get_serialized_errors(item, field_name) for item in detail)
    elif isinstance(detail, dict):
        serialized = (get_serialized_errors(value, key) for key, value in detail.items())
    else:
        code = drf_code_map[detail.code]
        return [Error(
            code=code,
            message=str(detail),
            target=field_name,
        ).serialize()]
    for serialized_errors in serialized:
        errors.extend(serialized_errors)
    return errors


class CoinMENAExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except CoinMENAException as exc:
            return JsonResponse(
                {
                    'errors': [e.serialize() for e in exc.errors]
                },
                status=exc.status_code,
                safe=False
            )
        return response


class CountryField(serializers.CharField):
    """Country code serializer field
    Handles 2-char country code in lowercase
    """

    def __init__(self, **kwargs):
        kwargs['max_length'] = 2
        kwargs['min_length'] = 2
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        country = pycountry.countries.get(alpha_2=validated.upper())
        if not country:
            self.fail('invalid')
        return country.alpha_2

    def to_representation(self, value):
        return super().to_representation(value).lower()


class LanguageField(serializers.CharField):
    """Language code serializer field
    Handles 2-char language code in lowercase
    """

    def __init__(self, **kwargs):
        kwargs['max_length'] = 2
        kwargs['min_length'] = 2
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        language = pycountry.languages.get(alpha_2=validated.lower())
        if not language:
            self.fail('invalid')
        return language.alpha_2

    def to_representation(self, value):
        return super().to_representation(value).lower()


class CurrencyField(serializers.CharField):
    """Currency code serializer field
    Handles 3-char currency code in lowercase
    """

    def __init__(self, **kwargs):
        kwargs['max_length'] = 3
        kwargs['min_length'] = 3
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        currency = pycountry.currencies.get(alpha_3=validated.upper())
        if not currency:
            self.fail('invalid')
        return currency.alpha_3

    def to_representation(self, value):
        return super().to_representation(value).lower()


class BaseValidator:
    default_error_messages: Optional[Dict[str, str]] = None
    errors = None

    def __init__(self):
        self.error_messages = self.default_error_messages or {}

    def initialize(self):
        self.errors = []

    def cleanup(self):
        self.errors = None

    def set_context(self, base):
        self.error_messages.update({
            key: message
            for key, message in base.error_messages.items()
            if key not in self.error_messages
        })
        self.initialize()

    def __call__(self, data):
        self.validate(data)
        self.raise_error()
        self.cleanup()

    def add_error(self, field, code, message=None):
        if message is None:
            message = self.error_messages[code]
        self.errors.append({
            field: ErrorDetail(message, code)
        })

    def validate(self, data):
        raise NotImplementedError

    def raise_error(self):
        if self.errors:
            raise ValidationError(self.errors)


class BaseFieldValidator(BaseValidator):
    def __init__(self):
        super(BaseFieldValidator, self).__init__()
        self.field_name = None

    def set_context(self, base):
        super(BaseFieldValidator, self).set_context(base)
        self.field_name = base.field_name

    def add_field_error(self, code, message=None):
        super(BaseFieldValidator, self).add_error(self.field_name, code, message)


class RegexValidator(BaseFieldValidator):
    def __init__(self, regex: str):
        super().__init__()
        self.regex = re.compile(regex)

    def validate(self, data: str) -> str:
        if not re.fullmatch(self.regex, data):
            self.add_field_error('invalid')
        return data


class AlwaysTrueFieldValidator(BaseFieldValidator):
    def validate(self, data: bool) -> None:
        if not data:
            self.add_field_error('required')


class WrapDataAPIViewMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super(WrapDataAPIViewMixin, self).dispatch(request, *args, **kwargs)
        if not response.exception:
            response.data = {
                'data': response.data
            }
        return response


class AssetPairDecimalField(serializers.DecimalField):
    def __init__(self, pair_id_source, decimals_source, pair_qs, *args, **kwargs):
        self.pair_qs = pair_qs
        self.pair_id_source = pair_id_source
        self.decimals_source = decimals_source
        kwargs['decimal_places'] = None
        kwargs['max_digits'] = None
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        data = smart_text(data)
        try:
            prepared = Decimal(data)
        except InvalidOperation:
            self.fail('invalid')
        if prepared.is_snan():
            self.fail('invalid')
        self.decimal_places = self.pair_qs.filter(
            pk=self.parent.initial_data[self.pair_id_source]
        ).values(self.decimals_source).first().get(self.decimals_source)
        self.max_digits = self.decimal_places + 10
        return super(AssetPairDecimalField, self).to_internal_value(data)

    def to_representation(self, value):
        self.decimal_places = self.pair_qs.filter(
            pk=getattr(self.parent.instance, self.pair_id_source)
        ).values(self.decimals_source).first().get(self.decimals_source)
        self.max_digits = self.decimal_places + 10
        return super().to_representation(value)

    def quantize(self, value):
        if value.is_snan():
            return value
        return super(AssetPairDecimalField, self).quantize(value)


class EnumField(serializers.ChoiceField):
    def __init__(self, enum_class, **kwargs):
        self.enum = enum_class
        kwargs['choices'] = [e.value for e in enum_class]
        super().__init__(**kwargs)

    def to_representation(self, value):
        if value:
            return value.value

    def to_internal_value(self, data):
        data = super(EnumField, self).to_internal_value(data)
        if data:
            return self.enum(data)
