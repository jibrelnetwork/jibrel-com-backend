import json
from typing import NamedTuple

import pytest
from django.http import JsonResponse
from rest_framework.exceptions import (
    APIException,
    ErrorDetail,
    ValidationError
)

from jibrel.core.errors import (
    CoinMENAException,
    Error,
    ErrorCode,
    UniqueException,
    WeakPasswordException
)
from jibrel.core.rest_framework import (
    CoinMENAExceptionMiddleware,
    drf_code_map,
    get_serialized_errors
)

drf_code1 = list(drf_code_map.keys())[0]
error_code1 = drf_code_map[drf_code1].value

drf_code2 = list(drf_code_map.keys())[1]
error_code2 = drf_code_map[drf_code2].value


class Case(NamedTuple):
    input: dict
    expected: list


cases = [
    Case(
        input={
            'field': [ErrorDetail('message', drf_code1)]
        },
        expected=[{'code': error_code1, 'message': 'message', 'target': 'field'}]
    ),
    Case(
        input={
            'field': [ErrorDetail('message1', drf_code1), ErrorDetail('message2', drf_code2)]
        },
        expected=[
            {'code': error_code1, 'message': 'message1', 'target': 'field'},
            {'code': error_code2, 'message': 'message2', 'target': 'field'}
        ]
    ),
    Case(
        input={
            'field1': [ErrorDetail('message1', drf_code1)],
            'field2': [ErrorDetail('message1', drf_code1)]
        },
        expected=[
            {'code': error_code1, 'message': 'message1', 'target': 'field1'},
            {'code': error_code1, 'message': 'message1', 'target': 'field2'}
        ]
    ),
    Case(
        input={
            'field1': [ErrorDetail('message1', drf_code1), ErrorDetail('message2', drf_code2)],
            'field2': [ErrorDetail('message1', drf_code1)]
        },
        expected=[
            {'code': error_code1, 'message': 'message1', 'target': 'field1'},
            {'code': error_code2, 'message': 'message2', 'target': 'field1'},
            {'code': error_code1, 'message': 'message1', 'target': 'field2'},
        ]
    ),
    Case(
        input={},
        expected=[]
    )
]


@pytest.mark.parametrize('drf,expected', cases)
def test_get_serialized_errors(drf, expected):
    assert get_serialized_errors(drf) == expected


@pytest.mark.parametrize(
    'exception',
    [
        UniqueException('field'),
        WeakPasswordException('field'),
        CoinMENAException.from_errors(
            Error(ErrorCode.REQUIRED, 'msg1', 'field1'),
            Error(ErrorCode.INVALID, 'msg2', 'field2'),
        )
    ]
)
def test_middleware(exception):
    def get_response(_):
        raise exception

    middleware = CoinMENAExceptionMiddleware(get_response)

    response = middleware(None)

    assert isinstance(response, JsonResponse)
    assert response.status_code == exception.status_code
    assert json.loads(response.content) == {'errors': [e.serialize() for e in exception.errors]}


@pytest.mark.parametrize('exception', [APIException, ValidationError, Exception])
def test_middleware_skips_other_exceptions(exception):
    def get_response(_):
        raise exception

    middleware = CoinMENAExceptionMiddleware(get_response)
    with pytest.raises(exception):
        middleware(None)
