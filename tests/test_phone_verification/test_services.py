import pytest

from jibrel.authentication.models import Phone
from jibrel.core.errors import ConflictException
from jibrel.kyc.models import PhoneVerification
from jibrel.kyc.services import (
    check_phone_verification,
    request_phone_verification
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


@pytest.mark.parametrize(
    'status',
    (
        Phone.UNCONFIRMED,
        Phone.CODE_REQUESTED,
        Phone.CODE_SENT,
        Phone.CODE_SUBMITTED,
        Phone.CODE_INCORRECT,
        Phone.EXPIRED,
        Phone.MAX_ATTEMPTS_REACHED,
        Phone.VERIFIED,
    )
)
@pytest.mark.parametrize('channel', (PhoneVerificationChannel.SMS, PhoneVerificationChannel.CALL))
@pytest.mark.django_db
def test_request_phone_verification(user_with_phone, mocker, channel, status):
    mock = mocker.patch('jibrel.kyc.services.send_verification_code.delay')
    phone = user_with_phone.profile.phone
    phone.status = status
    phone.save()
    request_phone_verification(user_with_phone, '127.0.0.1', phone, channel)
    mock.assert_called()
    assert phone.status == Phone.CODE_REQUESTED


@pytest.mark.parametrize(
    'status',
    (
        Phone.CODE_SENT,
        Phone.CODE_INCORRECT,

        pytest.param(Phone.UNCONFIRMED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(Phone.CODE_REQUESTED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(Phone.CODE_SUBMITTED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(Phone.EXPIRED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(Phone.MAX_ATTEMPTS_REACHED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(Phone.VERIFIED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
    )
)
@pytest.mark.django_db
def test_check_phone_verification(user_with_phone, mocker, status, verification_request_factory):
    mock = mocker.patch('jibrel.kyc.services.check_verification_code.apply_async')
    phone = user_with_phone.profile.phone
    phone.status = status
    phone.save()
    verification_request_factory(phone, PhoneVerification.PENDING)
    check_phone_verification(user_with_phone, '127.0.0.1', phone, '1234')
    mock.assert_called()
    assert phone.status == Phone.CODE_SUBMITTED
