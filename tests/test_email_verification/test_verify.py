import pytest
from django.contrib.auth.models import AnonymousUser

from jibrel.authentication.models import User
from jibrel.authentication.token_generator import verify_token_generator


@pytest.mark.django_db
def test_send_verification_email_user_disabled(client, user_disabled: User, mocker):
    email_mock = mocker.patch('jibrel.notifications.tasks.send_mail.delay')
    url = '/v1/auth/registration/confirmation-email-resend'
    client.force_login(user_disabled)
    response = client.post(url)
    assert response.status_code == 403
    email_mock.assert_not_called()


@pytest.mark.django_db
def test_verify_user_email_by_key_user_disabled(client, user_disabled: User, mocker):
    url = '/v1/auth/registration/email-verify'
    client.force_login(user_disabled)
    token = verify_token_generator.generate(user_disabled)
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 400
    assert isinstance(response.wsgi_request.user, AnonymousUser)
    assert 'key' in response.data.get('errors', {})


@pytest.mark.django_db
def test_verify_user(client, user_not_confirmed: User, mocker):
    url = '/v1/auth/registration/email-verify'
    client.force_login(user_not_confirmed)
    token = verify_token_generator.generate(user_not_confirmed)
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 200
    assert response.wsgi_request.user.is_email_confirmed is True


@pytest.mark.django_db
def test_verify_user_already_verified(client, user_confirmed_email: User, mocker):
    url = '/v1/auth/registration/email-verify'
    client.force_login(user_confirmed_email)
    token = verify_token_generator.generate(user_confirmed_email)
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 400
    assert response.wsgi_request.user.is_email_confirmed is True
    assert 'key' in response.data.get('errors', {})
