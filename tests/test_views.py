import pytest

from tests.test_payments.utils import validate_response_schema


@pytest.fixture()
def user(user_not_confirmed):
    password = 'password'
    user_not_confirmed.set_password(password)
    user_not_confirmed.save()
    user_not_confirmed._password = password
    return user_not_confirmed


@pytest.mark.urls('jibrel.authentication.auth_urls')
def test_register_is_allowed_to_anonymous(client):
    assert client.post('/registration').status_code != 403


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.auth_urls')
def test_register(client, mocker):
    mocker.patch('jibrel.authentication.views.send_verification_email')
    payload = {
        "email": "email@email.com",
        "password": "1very_very_long_password2",
        "userName": "nickname",
        "firstName": "name",
        "lastName": "surname",
        "isAgreedTerms": True,
        "isAgreedPrivacyPolicy": True,
        'language': 'EN',
    }
    response = client.post('/registration', payload)
    assert response.status_code == 200

    assert response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.auth_urls')
def test_login(client, user):
    payload = {
        'email': 'non_existent@email.com',
        'password': 'wrongpassword'
    }
    assert client.post('/login', payload).status_code == 403

    payload['email'] = user.email
    assert client.post('/login', payload).status_code == 403

    payload['password'] = user._password
    assert client.post('/login', payload).status_code == 200


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.user_urls')
def test_profile_not_confirmed(client, user_not_confirmed):
    client.force_login(user_not_confirmed)

    resp = client.get('/profile')
    assert resp.status_code == 200
    validate_response_schema('/v1/user/profile', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.user_urls')
def test_profile_confirmed_email(client, user_confirmed_email):
    client.force_login(user_confirmed_email)

    resp = client.get('/profile')
    assert resp.status_code == 200
    validate_response_schema('/v1/user/profile', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.user_urls')
def test_profile_with_phone(client, user_with_phone):
    client.force_login(user_with_phone)

    resp = client.get('/profile')
    assert resp.status_code == 200
    validate_response_schema('/v1/user/profile', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.user_urls')
def test_profile_with_confirmed_phone(client, user_with_confirmed_phone):
    client.force_login(user_with_confirmed_phone)

    resp = client.get('/profile')
    assert resp.status_code == 200
    validate_response_schema('/v1/user/profile', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.user_urls')
def test_profile_full_verified(client, full_verified_user):
    client.force_login(full_verified_user)

    resp = client.get('/profile')
    assert resp.status_code == 200
    validate_response_schema('/v1/user/profile', 'GET', resp)


@pytest.mark.django_db
@pytest.mark.urls('jibrel.authentication.auth_urls')
def test_force_login_after_password_changing(client, full_verified_user):
    old_password = 'D-iuW8OHDu'
    new_password = '@e&Mk/>D4n'
    url = '/password/change'
    body = {
        "oldPassword": old_password,
        "newPassword": new_password,
    }

    full_verified_user.set_password(old_password)
    full_verified_user.save()

    resp = client.post(url, body)
    assert resp.status_code == 403
    assert not resp.wsgi_request.user.is_authenticated

    client.force_login(full_verified_user)

    resp = client.post(url, body)
    assert resp.status_code == 200
    assert resp.wsgi_request.user.is_authenticated

    resp = client.post(url, body)
    assert resp.status_code == 400
    assert resp.wsgi_request.user.is_authenticated
