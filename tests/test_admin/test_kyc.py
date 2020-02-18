import pytest
from django.http import HttpResponseRedirect
from django.urls import reverse

from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)
from jibrel.kyc.tasks import enqueue_onfido_routine_task


@pytest.mark.django_db
def test_individual_kyc_view(admin_client, full_verified_user):
    model = IndividualKYCSubmission
    kyc = full_verified_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(kyc.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_organisational_kyc_view(admin_client, full_verified_organisational_user):
    model = OrganisationalKYCSubmission
    kyc = full_verified_organisational_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(kyc.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize(
    'fixture_user',
    ('full_verified_user', 'full_verified_organisational_user'),
)
@pytest.mark.parametrize(
    'tool,status,data',
    (
        ('approve', BaseKYCSubmission.APPROVED, None),
        ('reject', BaseKYCSubmission.REJECTED, {'reject_reason': 'blablabla'}),
    )
)
@pytest.mark.django_db
def test_kyc_approve_decline(admin_client, tool, status, data, fixture_user, getfixture, mocker):
    user = getfixture(fixture_user)
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


@pytest.mark.parametrize(
    'fixture_user',
    ('full_verified_user', 'full_verified_organisational_user'),
)
@pytest.mark.django_db
def test_kyc_force_onfido_routine(admin_client, fixture_user, getfixture, mocker):
    mock = mocker.patch('jibrel_admin.celery.app.send_task')
    user = getfixture(fixture_user)
    kyc = user.profile.last_kyc
    model = kyc.details.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'force_onfido_routine'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
    mock.assert_called()


@pytest.mark.parametrize(
    'fixture_user',
    ('full_verified_user', 'full_verified_organisational_user'),
)
@pytest.mark.django_db
def test_kyc_force_onfido_routine_task(fixture_user, getfixture, mocker):
    mock = mocker.patch('jibrel.kyc.tasks.enqueue_onfido_routine')
    mock_beneficiary = mocker.patch('jibrel.kyc.tasks.enqueue_onfido_routine_beneficiary')
    user = getfixture(fixture_user)
    kyc = user.profile.last_kyc
    enqueue_onfido_routine_task.s(kyc.account_type, kyc.pk).apply()
    mock.assert_called()
    if 'fixture_user' == 'full_verified_organisational_user':
        mock_beneficiary.assert_called()


@pytest.mark.parametrize(
    'fixture_user',
    ('full_verified_user', 'full_verified_organisational_user'),
)
@pytest.mark.django_db
def test_kyc_personal_agreement(admin_client, fixture_user, getfixture):
    user = getfixture(fixture_user)
    kyc = user.profile.last_kyc
    model = kyc.details.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'create_personal_agreement'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302

@pytest.mark.parametrize(
    'fixture_user',
    ('full_verified_user', 'full_verified_organisational_user'),
)
@pytest.mark.django_db
def test_kyc_clone(admin_client, fixture_user, getfixture):
    user = getfixture(fixture_user)
    kyc = user.profile.last_kyc
    model = kyc.details.__class__
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_actions', kwargs={
        'pk': kyc.pk,
        'tool': 'clone'
    })
    response = admin_client.get(url)
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
