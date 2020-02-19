import pytest
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.parametrize(
    'model,fixture,data',
    [
        (None, 'admin_user', {}),
        (Group, None, {
            'name': 'test'
        }),
        (None, 'full_verified_user', {}),
        (None, 'company', {}),
        (None, 'security_factory', {}),
        (None, 'offering_factory', {}),
        (None, 'subscription_agreement_template', {}),
        (None, 'application_factory', {}),
        (None, 'verified_individual_user_kyc', {}),
        (None, 'verified_organisational_user_kyc', {}),
        (None, 'external_call_log', {}),
        (None, 'cold_bank_account_factory', {}),
        (None, 'deposit_operation', {}),
        (None, 'refund_operation', {}),
    ]
)
@pytest.mark.django_db
def test_view_page(admin_client, fixture, model, data, get_fixture_obj):
    obj = get_fixture_obj(fixture, model, data)
    model = model or obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
