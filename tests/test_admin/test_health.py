import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    'url',
    [
        reverse(f'healthcheck'),
        reverse(f'prometheus-django-metrics'),
    ]
)
@pytest.mark.django_db
def test_changelist_page(client, url):
    response = client.get(url)
    assert response.status_code == 200
