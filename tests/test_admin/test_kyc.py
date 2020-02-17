import pytest
from django.http import HttpResponseRedirect
from django.urls import reverse

from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)


@pytest.mark.django_db
def test_individual_kyc_view(admin_client, full_verified_user):
    model = IndividualKYCSubmission
    kyc = full_verified_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(kyc.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200



@pytest.mark.parametrize(
    'tool,status,data',
    (
        ('approve', BaseKYCSubmission.APPROVED, None),
        ('reject', BaseKYCSubmission.REJECTED, {'reject_reason': 'blablabla'}),
    )
)
@pytest.mark.django_db
def test_individual_kyc_approve_decline(admin_client, full_verified_user, tool, status, data, mocker):
    user = full_verified_user
    email_mock = mocker.patch('jibrel.kyc.signals.handler.email_message_send')
    kyc = user.profile.last_kyc
    model = kyc.details.__class__
    kyc.status = BaseKYCSubmission.PENDING
    kyc.save()
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions',
        kwargs={
          'pk': kyc.pk,
          'tool': tool
        })
    response = admin_client.post(url, data) if data else admin_client.get(url)
    assert response.status_code == 302
    kyc.refresh_from_db()
    assert kyc.status == status
    email_mock.assert_called()


@pytest.mark.django_db
def test_individual_kyc_persoanl_agreement(admin_client, full_verified_user):
    model = IndividualKYCSubmission
    kyc = full_verified_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'create_personal_agreement'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302


@pytest.mark.django_db
def test_individual_kyc_clone(admin_client, full_verified_user):
    model = IndividualKYCSubmission
    kyc = full_verified_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'clone'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302


@pytest.mark.django_db
def test_organisational_kyc_view(admin_client, full_verified_organisational_user):
    model = OrganisationalKYCSubmission
    kyc = full_verified_organisational_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(kyc.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_organisational_kyc_persoanl_agreement(admin_client, full_verified_organisational_user):
    model = OrganisationalKYCSubmission
    kyc = full_verified_organisational_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'create_personal_agreement'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302


@pytest.mark.django_db
def test_organisational_kyc_clone(admin_client, full_verified_organisational_user):
    model = OrganisationalKYCSubmission
    kyc = full_verified_organisational_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'clone'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
