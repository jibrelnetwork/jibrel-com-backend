import uuid

import pytest
from django.contrib.auth.models import AnonymousUser

from jibrel.authentication.models import User
from jibrel.authentication.token_generator import verify_token_generator


@pytest.mark.django_db
def test_send_verification_email_user_disabled(client, user_disabled: User, mocker):
    email_mock = mocker.patch('jibrel.authentication.services.send_mail.delay')
    url = '/v1/auth/registration/confirmation-email-resend'
    client.force_login(user_disabled)
    response = client.post(url)
    assert response.status_code == 403
    email_mock.assert_not_called()


@pytest.mark.parametrize(
    'is_authenticated,token',
    (
        (True, 'abracadabra'),
        (False, str(uuid.uuid4())),
    )
)
@pytest.mark.django_db
def test_verify_user_email_invalid_token(client, user_not_confirmed: User,
                                         is_authenticated: bool, token: str):
    url = '/v1/auth/registration/email-verify'
    if is_authenticated:
        client.force_login(user_not_confirmed)
    response = client.post(
        url,
        {'key': 'abracadabra'}
    )
    assert response.status_code == 400
    assert isinstance(response.data['errors']['key'], list)
    user_not_confirmed.refresh_from_db()
    assert user_not_confirmed.is_email_confirmed is False
    if is_authenticated:
        assert response.wsgi_request.user.is_email_confirmed is False


@pytest.mark.parametrize(
    'is_authenticated',
    (
        (True,),
        (False,),
    )
)
@pytest.mark.django_db
def test_verify_user_email_by_key_user_disabled(client, user_disabled: User, is_authenticated: bool):
    url = '/v1/auth/registration/email-verify'
    user_disabled.is_email_confirmed = False
    user_disabled.save(update_fields=('is_email_confirmed',))
    if is_authenticated:
        client.force_login(user_disabled)
    token = verify_token_generator.generate(user_disabled)
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 409
    assert isinstance(response.wsgi_request.user, AnonymousUser)
    user_disabled.refresh_from_db()
    assert user_disabled.is_email_confirmed is False
    assert isinstance(response.data['errors']['detail'], list)


@pytest.mark.parametrize(
    'is_authenticated',
    (
        (True,),
        (False,),
    )
)
@pytest.mark.django_db
def test_verify_user(client, user_not_confirmed: User, is_authenticated: bool):
    url = '/v1/auth/registration/email-verify'
    if is_authenticated:
        client.force_login(user_not_confirmed)
    token = verify_token_generator.generate(user_not_confirmed)
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 200
    user_not_confirmed.refresh_from_db()
    assert user_not_confirmed.is_email_confirmed is True
    assert response.wsgi_request.user.is_email_confirmed is True


@pytest.mark.parametrize(
    'is_authenticated',
    (
        (True,),
        (False,),
    )
)
@pytest.mark.django_db
def test_verify_user_already_verified(client, user_confirmed_email: User, is_authenticated: bool):
    url = '/v1/auth/registration/email-verify'
    if is_authenticated:
        client.force_login(user_confirmed_email)
    token = verify_token_generator.generate(user_confirmed_email)
    assert user_confirmed_email.is_email_confirmed is True
    response = client.post(
        url,
        {'key': token}
    )
    assert response.status_code == 409
    user_confirmed_email.refresh_from_db()
    assert user_confirmed_email.is_email_confirmed is True
    assert isinstance(response.data['errors']['detail'], list)
    if is_authenticated:
        assert response.wsgi_request.user.is_email_confirmed is True
