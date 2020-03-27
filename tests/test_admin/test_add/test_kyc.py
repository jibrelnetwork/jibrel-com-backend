import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_change(admin_client, verified_organisational_user_kyc):
    obj = verified_organisational_user_kyc
    url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.post(url, {
        'beneficiaries-TOTAL_FORMS': 1,
        'beneficiaries-INITIAL_FORMS': 1,
        'directors-TOTAL_FORMS': 1,
        'directors-INITIAL_FORMS': 1,
        'company_address_registered-TOTAL_FORMS': 1,
        'company_address_registered-INITIAL_FORMS': 1,
        'company_address_principal-TOTAL_FORMS': 1,
        'company_address_principal-INITIAL_FORMS': 0
    })
    assert response.status_code == 200
    assert b'Please correct the errors below.' in response.content
