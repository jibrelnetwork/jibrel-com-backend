from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from jibrel.authentication.factories import VerifiedUser

from .utils import validate_response_schema


@pytest.mark.django_db
def test_limits_endpoint():
    client = APIClient()
    user = VerifiedUser.create()
    client.force_authenticate(user)

    resp = client.get('/v1/payments/limits')
    assert resp.status_code == 200

    assert len(resp.data['data']) > 0

    validate_response_schema('/v1/payments/limits', 'GET', resp)

    assert Decimal(resp.data['data'][0]['total']) == Decimal(0), resp.data
    assert Decimal(resp.data['data'][0]['available']) == Decimal(0)
