import uuid

import pytest

from jibrel.authentication.models import User
from jibrel.authentication.services import (
    activate_password_reset,
    reset_password_complete
)
from jibrel.authentication.token_generator import (
    activate_reset_password_token_generator,
    complete_reset_password_token_generator
)


@pytest.mark.django_db
def test_activate_password_reset(user_with_confirmed_phone: User, mocker):
    mocker.patch.object(activate_reset_password_token_generator, 'validate', return_value=user_with_confirmed_phone)
    token = uuid.uuid4()
    activate_password_reset(token)
    assert user_with_confirmed_phone == complete_reset_password_token_generator.validate(token)


@pytest.mark.django_db
def test_reset_password_complete(user_with_confirmed_phone: User, mocker):
    mocker.patch.object(complete_reset_password_token_generator, 'validate', return_value=user_with_confirmed_phone)
    mocker.patch('jibrel.authentication.services.validate_password')
    password = '123'
    reset_password_complete(uuid.uuid4(), password)
    assert user_with_confirmed_phone.check_password(password)
