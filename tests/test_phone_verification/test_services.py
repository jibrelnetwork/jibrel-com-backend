import pytest

from jibrel.authentication.enum import PhoneStatus
from jibrel.core.errors import ConflictException
from jibrel.kyc.enum import PhoneVerificationStatus
from jibrel.kyc.services import (
    check_phone_verification,
    request_phone_verification
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


@pytest.mark.parametrize(
    'status',
    (
        PhoneStatus.UNCONFIRMED,
        PhoneStatus.CODE_REQUESTED,
        PhoneStatus.CODE_SENT,
        PhoneStatus.CODE_SUBMITTED,
        PhoneStatus.CODE_INCORRECT,
        PhoneStatus.EXPIRED,
        PhoneStatus.MAX_ATTEMPTS_REACHED,
        PhoneStatus.VERIFIED,
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
    assert phone.status == PhoneStatus.CODE_REQUESTED


@pytest.mark.parametrize(
    'status',
    (
        PhoneStatus.CODE_SENT,
        PhoneStatus.CODE_INCORRECT,

        pytest.param(PhoneStatus.UNCONFIRMED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(PhoneStatus.CODE_REQUESTED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(PhoneStatus.CODE_SUBMITTED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(PhoneStatus.EXPIRED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(PhoneStatus.MAX_ATTEMPTS_REACHED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
        pytest.param(PhoneStatus.VERIFIED, marks=pytest.mark.xfail(strict=True, raises=ConflictException)),
    )
)
@pytest.mark.django_db
def test_check_phone_verification(user_with_phone, mocker, status, verification_request_factory):
    mock = mocker.patch('jibrel.kyc.services.check_verification_code.apply_async')
    phone = user_with_phone.profile.phone
    phone.status = status
    phone.save()
    verification_request_factory(phone, PhoneVerificationStatus.PENDING)
    check_phone_verification(user_with_phone, '127.0.0.1', phone, '1234')
    mock.assert_called()
    assert phone.status == PhoneStatus.CODE_SUBMITTED
