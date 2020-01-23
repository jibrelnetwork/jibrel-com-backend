import pytest
from django.urls import reverse

from jibrel.kyc.models import (
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


@pytest.mark.django_db
def test_individual_kyc_approve(admin_client, full_verified_user):
    pass


@pytest.mark.django_db
def test_individual_kyc_decline(admin_client, full_verified_user):
    pass


@pytest.mark.django_db
def test_organisational_kyc_view(admin_client, full_verified_organisational_user):
    model = OrganisationalKYCSubmission
    kyc = full_verified_organisational_user.profile.last_kyc
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change', args=(kyc.pk,))
    response = admin_client.get(url)
    assert response.status_code == 200
