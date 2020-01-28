import pytest
from django.urls import reverse

from jibrel.authentication.models import User


@pytest.mark.django_db
def test_user_view(admin_client, full_verified_user):
    model = User
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(full_verified_user.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
