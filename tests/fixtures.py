import pytest

from jibrel.authentication.factories import VerifiedUser
from jibrel.authentication.models import (
    Phone,
    Profile,
    User
)
from jibrel.notifications.models import ExternalServiceCallLog

# from jibrel.payments.models import Fee


@pytest.fixture()
def user_not_confirmed_factory(db):
    cnt = 0

    def _user_not_confirmed_factory():
        nonlocal cnt
        user = User.objects.create(
            email=f'example{cnt}@example.com',
            is_email_confirmed=False,
        )
        Profile.objects.create(
            user=user,
            username='example',
            is_agreed_documents=True,
            language='en',
        )
        cnt += 1
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
            number='971545559508'
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
def full_verified_user_factory(full_verified_user):
    def factory(country):
        full_verified_user.profile.last_basic_kyc.residency = country
        full_verified_user.profile.last_basic_kyc.save()
        return full_verified_user
    return factory


# @pytest.fixture
# def off_fees(db):
#     state = Fee.objects.all().values()
#     Fee.objects.all().update(value=0, value_type=Fee.VALUE_TYPE_CONSTANT)
#     yield
#     for fee in state:
#         id = fee.pop('uuid')
#         Fee.objects.filter(uuid=id).update(**fee)


# @pytest.fixture
# def set_default_fee_for_operation(db):
#     state = Fee.objects.all().values()
#
#     def f(operation_type, value, value_type=Fee.VALUE_TYPE_CONSTANT):
#         value = Decimal(value)
#         Fee.objects.create(operation_type=operation_type, value=value, value_type=value_type)
#
#     yield f
#
#     for fee in state:
#         id = fee.pop('uuid')
#         Fee.objects.filter(uuid=id).update(**fee)
