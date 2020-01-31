import pytest

from jibrel.authentication.factories import ApprovedIndividualKYCFactory
from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission
)


@pytest.mark.django_db
def test_approved_kyc_permissions(
    client,
    user_with_confirmed_phone,
):
    url = '/v1/kyc/approved'
    response = client.get(url)
    assert response.status_code == 403

    client.force_login(user_with_confirmed_phone)
    response = client.get(url)
    assert response.status_code == 409


@pytest.mark.django_db
def test_approved_kyc_personal(
    client,
    full_verified_user,
):
    url = '/v1/kyc/approved'
    client.force_login(full_verified_user)
    response = client.get(url)

    assert response.status_code == 200

    last_kyc = full_verified_user.profile.last_kyc.details

    assert response.data['accountType'] == BaseKYCSubmission.INDIVIDUAL
    assert response.data['firstName'] == last_kyc.first_name
    assert response.data['lastName'] == last_kyc.last_name
    assert response.data['middleName'] == last_kyc.middle_name

    assert response.data['streetAddress'] == last_kyc.street_address
    assert response.data['apartment'] == last_kyc.apartment
    assert response.data['city'] == last_kyc.city
    assert response.data['postCode'] == last_kyc.post_code
    assert response.data['country'] == last_kyc.country


@pytest.mark.django_db
def test_approved_kyc_orgaziational(
    client,
    full_verified_organisational_user,
):
    url = '/v1/kyc/approved'
    client.force_login(full_verified_organisational_user)
    response = client.get(url)

    assert response.status_code == 200

    last_kyc = full_verified_organisational_user.profile.last_kyc.details
    company_address_registered = last_kyc.company_address_registered

    assert response.data['accountType'] == BaseKYCSubmission.BUSINESS
    assert response.data['companyName'] == last_kyc.company_name

    assert response.data['companyAddressRegistered']['streetAddress'] == company_address_registered.street_address
    assert response.data['companyAddressRegistered']['apartment'] == company_address_registered.apartment
    assert response.data['companyAddressRegistered']['city'] == company_address_registered.city
    assert response.data['companyAddressRegistered']['postCode'] == company_address_registered.post_code
    assert response.data['companyAddressRegistered']['country'] == company_address_registered.country

@pytest.mark.django_db
def test_kyc_ordering(
    client,
    full_verified_user,
):
    profile = full_verified_user.profile
    last_kyc = full_verified_user.profile.last_kyc.details
    submissions = [ApprovedIndividualKYCFactory.create(
        profile=profile,
        passport_document__profile=profile,
        proof_of_address_document__profile=profile,
        status=IndividualKYCSubmission.PENDING
    ) for _i in range(5)]
    profile.refresh_from_db()
    assert submissions[0].status == IndividualKYCSubmission.PENDING
    assert profile.last_kyc.pk == last_kyc.pk

    # approve another kyc. As soon as it created later - it became active
    last_kyc.reject()
    profile.refresh_from_db()
    assert profile.last_kyc is None

    last_kyc.approve()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == last_kyc.pk

    # approve another kyc. As soon as it created later - it became active
    submissions[0].approve()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == submissions[0].base_kyc_id

    submissions[3].approve()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == submissions[3].base_kyc_id

    # approve another kyc. But the latest one is still active
    submissions[2].approve()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == submissions[3].base_kyc_id

    # reject some kyc
    last_kyc.reject()
    submissions[1].reject()
    submissions[4].reject()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == submissions[3].base_kyc_id

    # test clone and reject
    one_more_kyc = last_kyc.clone()
    one_more_kyc.reject()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == submissions[3].base_kyc_id

    # text clone. check if it set as active
    another_kyc = last_kyc.clone()
    another_kyc.approve()
    profile.refresh_from_db()
    assert profile.last_kyc.pk == another_kyc.base_kyc_id
