import pytest


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
def test_approved_kyc(
    client,
    full_verified_user,
):
    url = '/v1/kyc/approved'
    client.force_login(full_verified_user)
    response = client.get(url)

    assert response.status_code == 200

    last_kyc = full_verified_user.profile.last_kyc.details
    assert response.data['firstName'] == last_kyc.first_name
    assert response.data['lastName'] == last_kyc.last_name
    assert response.data['middleName'] == last_kyc.middle_name

    assert response.data['streetAddress'] == last_kyc.street_address
    assert response.data['apartment'] == last_kyc.apartment
    assert response.data['city'] == last_kyc.city
    assert response.data['postCode'] == last_kyc.post_code
    assert response.data['country'] == last_kyc.country
