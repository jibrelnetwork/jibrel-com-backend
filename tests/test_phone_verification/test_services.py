import pytest

from jibrel.authentication.models import Phone
from jibrel.kyc.services import request_phone_verification
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
    mocker.patch('jibrel.kyc.services.ResendVerificationSMSLimiter.is_throttled')
    mock = mocker.patch('jibrel.kyc.services.send_verification_code.delay')
    phone = user_with_phone.profile.phone
    phone.status = status
    phone.save()
    request_phone_verification(user_with_phone, '127.0.0.1', phone, channel)
    mock.assert_called()
    assert phone.status == Phone.CODE_REQUESTED
