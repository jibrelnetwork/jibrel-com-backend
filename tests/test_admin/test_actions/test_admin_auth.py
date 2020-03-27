import pytest
from django.contrib.auth.models import (
    Group,
    User
)
from django.urls import reverse


@pytest.mark.django_db
def test_user_create(admin_client, admin_user):
    model = User
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_add')
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_post(admin_client, admin_user):
    model = User
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(admin_user.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200






@pytest.mark.django_db
def test_group_post(admin_client):
    pass


@pytest.mark.django_db
def test_group_delete(admin_client):
    pass
