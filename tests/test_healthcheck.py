import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def client():
    client = APIClient()

    return client


def test_healthcheck_endpoint(client):
    resp = client.get('/healthcheck')
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data['healthy'] == True
    assert resp.data['version']
