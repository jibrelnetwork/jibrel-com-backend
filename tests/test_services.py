from os import urandom
from uuid import uuid4

import pytest

from jibrel.authentication.services import (
    change_password,
    register,
    validate_password
)
from jibrel.core.errors import UniqueException, WeakPasswordException


@pytest.fixture
def weak_password():
    return '1'  # assuming 1 is a weak password


@pytest.fixture
def strong_password():
    return str(urandom(25))  # assuming 25 symbols from urandom is a good password


def test_validate_password(weak_password, strong_password):
    with pytest.raises(WeakPasswordException):
        validate_password(weak_password)

    validate_password(strong_password)


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

    with pytest.raises(UniqueException):
        register(**params)


@pytest.fixture
def user(django_user_model):
    user = django_user_model(uuid=uuid4(), email='email@email.com', is_email_confirmed=True)
    user.set_password(django_user_model.objects.make_random_password())
    user.save()
    return user


@pytest.mark.django_db
def test_change_password(user, strong_password, weak_password):
    password = 'password'
    user.set_password(password)
    user.save()

    change_password(user, password, strong_password)

    assert user.check_password(strong_password)

    with pytest.raises(WeakPasswordException):
        change_password(user, strong_password, weak_password)
