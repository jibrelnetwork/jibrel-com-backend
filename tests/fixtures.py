from decimal import Decimal

import pytest

from jibrel.authentication.factories import VerifiedUser
from jibrel.authentication.models import Phone, Profile, User
from jibrel.notifications.models import ExternalServiceCallLog
from jibrel.payments.models import Fee


@pytest.fixture
def user_not_confirmed(db):
    user = User.objects.create(
        email='example@example.com',
        is_email_confirmed=False,
    )
    Profile.objects.create(
        user=user,
        username='example',
        is_agreed_privacy_policy=True,
        is_agreed_terms=True,
        language='en',
    )
    return user


@pytest.fixture
def user_confirmed_email(user_not_confirmed, db):
    user_not_confirmed.is_email_confirmed = True
    user_not_confirmed.save()
    return user_not_confirmed


@pytest.fixture
def user_with_phone(user_confirmed_email, db):
    Phone.objects.create(
        profile=user_confirmed_email.profile,
        code='971',
        number='545559508'
    )
    return user_confirmed_email


@pytest.fixture
def user_with_confirmed_phone(user_with_phone, db):
    phone = user_with_phone.profile.phone
    phone.is_confirmed = True
    phone.save()
    return user_with_phone


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
def full_verified_user_factory(full_verified_user):
    def factory(country):
        full_verified_user.profile.last_basic_kyc.residency = country
        full_verified_user.profile.last_basic_kyc.save()
        return full_verified_user
    return factory


@pytest.fixture
def off_fees(db):
    state = Fee.objects.all().values()
    Fee.objects.all().update(value=0, value_type=Fee.VALUE_TYPE_CONSTANT)
    yield
    for fee in state:
        id = fee.pop('uuid')
        Fee.objects.filter(uuid=id).update(**fee)


@pytest.fixture
def set_default_fee_for_operation(db):
    state = Fee.objects.all().values()

    def f(operation_type, value, value_type=Fee.VALUE_TYPE_CONSTANT):
        value = Decimal(value)
        Fee.objects.create(operation_type=operation_type, value=value, value_type=value_type)

    yield f

    for fee in state:
        id = fee.pop('uuid')
        Fee.objects.filter(uuid=id).update(**fee)
