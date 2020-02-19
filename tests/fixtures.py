from uuid import uuid4

import pytest

from jibrel.authentication.models import (
    Phone,
    Profile,
    User
)
from jibrel.notifications.models import ExternalServiceCallLog
from tests.factories import (
    VerifiedOrganisationalUser,
    VerifiedUser
)


@pytest.fixture()
def user_not_confirmed_factory(db):
    def _user_not_confirmed_factory():
        user = User.objects.create(
            email=f'{uuid4()}@example.com',
            is_email_confirmed=False,
        )
        Profile.objects.create(
            user=user,
            username='example',
            first_name='John',
            last_name='Smith',
            is_agreed_documents=True,
            language='en',
        )
        return user
    return _user_not_confirmed_factory


@pytest.fixture
def user_not_confirmed(user_not_confirmed_factory):
    return user_not_confirmed_factory()


@pytest.fixture
def user_confirmed_email_factory(user_not_confirmed_factory):
    def _user_confirmed_email_factory():
        user_not_confirmed = user_not_confirmed_factory()
        user_not_confirmed.is_email_confirmed = True
        user_not_confirmed.save()
        return user_not_confirmed
    return _user_confirmed_email_factory


@pytest.fixture
def user_confirmed_email(user_confirmed_email_factory):
    return user_confirmed_email_factory()


@pytest.fixture
def user_with_phone_factory(user_confirmed_email_factory):
    def _user_with_phone_factory():
        user_confirmed_email = user_confirmed_email_factory()
        Phone.objects.create(
            profile=user_confirmed_email.profile,
            number='971545559508',
            is_primary=True
        )
        return user_confirmed_email
    return _user_with_phone_factory


@pytest.fixture
def user_with_phone(user_with_phone_factory):
    return user_with_phone_factory()


@pytest.fixture
def user_with_confirmed_phone(user_with_phone, db):
    phone = user_with_phone.profile.phone
    phone.status = Phone.VERIFIED
    phone.save()
    return user_with_phone


@pytest.fixture
def user_disabled(user_confirmed_email, db):
    user_confirmed_email.is_active = False
    user_confirmed_email.save()
    return user_confirmed_email


DEFAULT_ACTION_TYPE = ExternalServiceCallLog.PHONE_CHECK_VERIFICATION


@pytest.fixture
def external_call_log(user_confirmed_email, db):
    return ExternalServiceCallLog.objects.create(
        initiator=user_confirmed_email,
        initiator_ip='127.0.0.1',
        action_type=DEFAULT_ACTION_TYPE,
        kwargs={},
    )


@pytest.fixture
def full_verified_user():
    return VerifiedUser.create()


@pytest.fixture
def full_verified_organisational_user():
    return VerifiedOrganisationalUser.create()


@pytest.fixture
def full_verified_user_factory(full_verified_user):
    def factory(country='ru'):
        full_verified_user.profile.last_kyc.residency = country
        full_verified_user.profile.last_kyc.save()
        return full_verified_user
    return factory


@pytest.fixture
def get_fixture(request):
    def _get_fixture(name):
        return request.getfixturevalue(name)
    return _get_fixture


@pytest.fixture
def get_fixture_obj(get_fixture):
    def _get_fixture_obj(name, model, data=None):
        data = data or {}
        if name:
            fixture = get_fixture(name)
            return fixture(**data) if callable(fixture) else fixture
        return model.objects.create(**data)
    return _get_fixture_obj
