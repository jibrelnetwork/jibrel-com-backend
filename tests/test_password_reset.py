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
def test_activate_password_reset(user_with_confirmed_phone: User):
    token = activate_reset_password_token_generator.generate(user_with_confirmed_phone)
    activate_password_reset(token)
    assert user_with_confirmed_phone == complete_reset_password_token_generator.validate(token).user


@pytest.mark.django_db
def test_reset_password_complete(user_with_confirmed_phone: User):
    token = complete_reset_password_token_generator.generate(user_with_confirmed_phone)
    password = '123'
    reset_password_complete(token, password)
    user_with_confirmed_phone.refresh_from_db()
    assert user_with_confirmed_phone.check_password(password)
