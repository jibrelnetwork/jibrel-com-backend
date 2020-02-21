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
def test_read(admin_client, fixture, model, data, get_fixture_obj):
    obj = get_fixture_obj(fixture, model, data)
    model = model or obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    'model,fixture,data,post_data',
    [
        (None, 'admin_user', {}, {}),
        (Group, None, {
            'name': 'test'
        }, {}),
        (None, 'full_verified_user', {}, {
            'profile-TOTAL_FORMS': 1,
            'profile-INITIAL_FORMS': 1,
            'profile-0-phones-TOTAL_FORMS': 0,
            'profile-0-phones-INITIAL_FORMS': 0
        }),
        (None, 'company', {}, {}),
        (None, 'security_factory', {}, {}),
        (None, 'offering_factory', {}, {}),
        (None, 'subscription_agreement_template', {}, {}),
        (None, 'application_factory', {}, {}),
        (None, 'verified_individual_user_kyc', {}, {}),
        (None, 'verified_organisational_user_kyc', {}, {
            'beneficiaries-TOTAL_FORMS': 1,
            'beneficiaries-INITIAL_FORMS': 1,
            'directors-TOTAL_FORMS': 1,
            'directors-INITIAL_FORMS': 1,
            'company_address_registered-TOTAL_FORMS': 1,
            'company_address_registered-INITIAL_FORMS': 1,
            'company_address_principal-TOTAL_FORMS': 1,
            'company_address_principal-INITIAL_FORMS': 0
        }),
        (None, 'cold_bank_account_factory', {}, {}),
    ]
)
@pytest.mark.django_db
def test_change(admin_client, fixture, model, data, post_data, get_fixture_obj):
    obj = get_fixture_obj(fixture, model, data)
    model = model or obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(obj.pk,))
    response = admin_client.post(url, post_data)
    assert response.status_code == 200
