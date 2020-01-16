import pytest

from jibrel.kyc.models import BaseKYCSubmission


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
