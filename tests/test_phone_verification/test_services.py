import pytest

from jibrel.kyc.services import request_phone_verification
from jibrel.kyc.tasks import send_verification_code


@pytest.mark.django_db
def test_request_phone_verification_sends_task(user_with_phone, mocker):
    mocked = mocker.patch.object(send_verification_code, 'delay')
    request_phone_verification(user_with_phone, '127.0.0.1', user_with_phone.profile.phone)
    mocked.assert_called()
