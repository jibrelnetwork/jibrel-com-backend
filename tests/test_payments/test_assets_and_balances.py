import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django_banking.models import Asset
from jibrel.authentication.factories import VerifiedUser

from .utils import validate_response_schema


@pytest.fixture
def client():
    client = APIClient()

    return client


@pytest.mark.django_db
def test_assets_list(client):
    user = VerifiedUser.create()
    client.force_authenticate(user)
    resp = client.get('/v1/payments/assets/')
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.data, list)
    assert len(resp.data) == Asset.objects.all().count()
    validate_response_schema('/v1/payments/assets', 'GET', resp)
