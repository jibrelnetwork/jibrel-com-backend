import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_change(admin_client, full_verified_user):
    obj = full_verified_user
    url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.post(url, {
        'profile-TOTAL_FORMS': 1,
        'profile-INITIAL_FORMS': 1,
        'profile-0-phones-TOTAL_FORMS': 1,
        'profile-0-phones-INITIAL_FORMS': 1
    })
    assert response.status_code == 200
    assert b'Please correct the errors below.' in response.content
