import re

import pycountry
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import (
    exceptions,
    serializers
)
from rest_framework.response import Response
from rest_framework.views import set_rollback


def exception_handler(exc, context):
    """Copypaste from `rest_framework.views.exception_handler`
     with changed `exc.detail` to `exc.get_full_details()` and wrapped all errors in `errors` key
    """

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait
        if isinstance(exc.detail, (list, dict)):
            errors = exc.get_full_details()
        else:
            errors = {'detail': exc.get_full_details()}

        set_rollback()
        response_data = {'errors': errors}
        if hasattr(exc, 'data') and exc.data is not None:
            response_data['data'] = exc.data
        return Response(response_data, status=exc.status_code, headers=headers)

    return None


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


class RegexValidator:
    requires_context = True

    def __init__(self, regex: str):
        self.regex = re.compile(regex)

    def __call__(self, data: str, serializer_field: serializers.Field) -> None:
        if not re.fullmatch(self.regex, data):
            serializer_field.fail('invalid')


class AlwaysTrueFieldValidator:
    requires_context = True

    def __call__(self, data: bool, serializer_field: serializers.Field) -> None:
        if not data:
            serializer_field.fail('required')


class WrapDataAPIViewMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super(WrapDataAPIViewMixin, self).dispatch(request, *args, **kwargs)
        if not response.exception:
            response.data = {
                'data': response.data
            }
        return response


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
