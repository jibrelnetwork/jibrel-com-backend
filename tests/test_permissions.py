import itertools

import pytest

from jibrel.authentication.models import Profile

ANONYMOUS_ROUTES = [
    ('POST', '/v1/auth/registration'),
    ('POST', '/v1/auth/registration/email-verify'),
    ('POST', '/v1/auth/login'),
    ('POST', '/v1/auth/password/reset'),
    ('POST', '/v1/auth/password/reset/activate'),
    ('POST', '/v1/auth/password/reset/complete'),
]

UNVERIFIED_ROUTES = [
    ('POST', '/v1/auth/registration/confirmation-email-resend'),
    ('POST', '/v1/auth/logout'),
    ('GET', '/v1/user/profile'),
    ('GET', '/v1/user/limits'),
]

REQUIRED_VERIFIED_ONLY_EMAIL_ROUTES = [
    ('POST', '/v1/auth/password/change'),
    ('POST', '/v1/kyc/phone'),
    ('POST', '/v1/kyc/phone/resend-sms'),
    ('POST', '/v1/kyc/phone/call-me'),
    ('POST', '/v1/kyc/phone/verify'),
]

REQUIRED_VERIFIED_PHONE_AND_EMAIL_ROUTES = [
    ('POST', '/v1/kyc/individual'),
    ('POST', '/v1/kyc/organization'),
]


@pytest.mark.django_db
@pytest.mark.parametrize('method,route', ANONYMOUS_ROUTES)
def test_positive_anonymous_permission(method, route, client):
    response = client.generic(method=method, path=route)
    assert response.status_code != 403


@pytest.mark.django_db
@pytest.mark.parametrize('method,route', itertools.chain(UNVERIFIED_ROUTES, ANONYMOUS_ROUTES))
def test_positive_unverified_email_permission(method, route, client, user_not_confirmed, mocker):
    mocker.patch('jibrel.notifications.tasks.send_mail.delay')
    client.force_login(user_not_confirmed)
    response = client.generic(method=method, path=route)
    assert response.status_code != 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    'method,route',
    itertools.chain(REQUIRED_VERIFIED_ONLY_EMAIL_ROUTES, UNVERIFIED_ROUTES, ANONYMOUS_ROUTES)
)
def test_positive_verified_email_permission(method, route, client, user_confirmed_email, mocker):
    mocker.patch('jibrel.kyc.services.request_phone_verification')
    client.force_login(user_confirmed_email)
    response = client.generic(method=method, path=route)
    assert response.status_code != 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    'method,route',
    itertools.chain(
        REQUIRED_VERIFIED_PHONE_AND_EMAIL_ROUTES,
        REQUIRED_VERIFIED_ONLY_EMAIL_ROUTES,
        UNVERIFIED_ROUTES,
        ANONYMOUS_ROUTES
    )
)
def test_positive_verified_phone_and_email_permission(method, route, client, user_with_confirmed_phone, mocker):
    mocker.patch('jibrel.kyc.services.request_phone_verification')
    client.force_login(user_with_confirmed_phone)
    response = client.generic(method=method, path=route)
    assert response.status_code != 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    'method,route',
    itertools.chain(
        REQUIRED_VERIFIED_PHONE_AND_EMAIL_ROUTES,
        REQUIRED_VERIFIED_ONLY_EMAIL_ROUTES,
        UNVERIFIED_ROUTES,
    )
)
def test_negative_anonymous_permission(method, route, client, mocker):
    mocker.patch('jibrel.kyc.services.request_phone_verification')
    response = client.generic(method=method, path=route)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    'method,route',
    itertools.chain(
        REQUIRED_VERIFIED_ONLY_EMAIL_ROUTES,
        REQUIRED_VERIFIED_PHONE_AND_EMAIL_ROUTES,
    )
)
def test_negative_unverified_email_permission(method, route, client, user_not_confirmed, mocker):
    mocker.patch('jibrel.kyc.services.request_phone_verification')
    client.force_login(user_not_confirmed)
    response = client.generic(method=method, path=route)
    assert response.status_code in {403, 409}


@pytest.mark.parametrize('method,route', REQUIRED_VERIFIED_PHONE_AND_EMAIL_ROUTES)
def test_kyc_pending(client, user_with_confirmed_phone, method, route):
    user_with_confirmed_phone.profile.kyc_status = Profile.KYC_PENDING
    user_with_confirmed_phone.profile.save()
    client.force_login(user_with_confirmed_phone)
    response = client.generic(method=method, path=route)
    assert response.status_code == 409
