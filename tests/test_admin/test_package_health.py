import pytest
from django.contrib import admin
from django.urls import reverse


@pytest.mark.parametrize(
    'url',
    [
        '/admin/',
        *(
            reverse(f'admin:{app._meta.app_label}_{app._meta.model_name}_changelist')
            for app in admin.site._registry
        )
    ]
)
@pytest.mark.django_db
def test_app_page_is_available(admin_client, url):
    response = admin_client.get(url)
    assert response.status_code == 200
