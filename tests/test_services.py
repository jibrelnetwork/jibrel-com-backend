from os import urandom

import pytest

from jibrel.authentication.services import (
    register,
)


@pytest.fixture
def strong_password():
    return str(urandom(25))  # assuming 25 symbols from urandom is a good password


@pytest.mark.django_db
def test_register(strong_password, mocker):
    mocker.patch('jibrel.authentication.views.send_verification_email')
    params = {
        'email': 'email@email.com',
        'password': strong_password,
        'username': 'username',
        'is_agreed_terms': True,
        'is_agreed_privacy_policy': True,
        'language': 'EN',
    }
    profile = register(**params)
    assert profile
    assert profile.user
    assert profile.user.email == params['email']
    assert profile.user.check_password(strong_password)
