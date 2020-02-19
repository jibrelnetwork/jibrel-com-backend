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
        (None, 'admin_user', {}),
        (None, 'company', {}),
        (None, 'security_factory', {}),
        (None, 'offering_factory', {}),
        (None, 'subscription_agreement_template', {}),
    ]
)
@pytest.mark.django_db
def test_delete(admin_client, fixture, model, data, get_fixture_obj):
    obj = get_fixture_obj(fixture, model, data)
    model = model or obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_delete', args=(obj.pk,))
    response = admin_client.post(url, {'post': 'yes'})
    assert 'was deleted successfully.' in response.cookies['messages']._value
    assert response.status_code == 302
    assert model.objects.filter(pk=obj.pk).exists() is False


@pytest.mark.parametrize(
    'model,fixture,data',
    [
        (None, 'full_verified_organisational_user', {}),
        (None, 'full_verified_user', {}),
        (None, 'user_with_confirmed_phone', {}),
        (None, 'user_with_phone', {}),
        (None, 'user_confirmed_email', {}),
        (None, 'user_not_confirmed', {}),
        # investment application has its own test
        (None, 'verified_individual_user_kyc', {}),
        (None, 'verified_organisational_user_kyc', {}),
        (None, 'external_call_log', {}),
        (None, 'cold_bank_account_factory', {}),
        (None, 'deposit_operation', {}),
        (None, 'refund_operation', {}),
    ]
)
@pytest.mark.django_db
def test_delete_restricted(admin_client, fixture, model, data, get_fixture_obj):
    obj = get_fixture_obj(fixture, model, data)
    model = model or obj.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_delete', args=(obj.pk,))
    response = admin_client.post(url, {'post': 'yes'})
    assert response.status_code == 403
    assert model.objects.filter(pk=obj.pk).exists() is True
