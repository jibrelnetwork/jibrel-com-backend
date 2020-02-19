import pytest
from django.contrib import admin
from django.urls import reverse

APP_ALL = set(admin.site._registry.keys())


@pytest.mark.parametrize(
    'url',
    [
        '/admin/',
        *(
            reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
            for model in admin.site._registry
        )
    ]
)
@pytest.mark.django_db
def test_changelist_page(admin_client, url):
    response = admin_client.get(url)
    assert response.status_code == 200
