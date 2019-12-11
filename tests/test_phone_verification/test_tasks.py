import json
from uuid import uuid4

import pytest

from jibrel.kyc.models import PhoneVerification
from jibrel.kyc.tasks import (
    check_verification_code,
    send_verification_code,
    twilio_verify_api
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


class MockRequest:
    body = ''


class MockResponse:
    def __init__(self, json_data):
        self._json = json_data
        self.text = json.dumps(json_data)
        self.request = MockRequest()
        self.ok = True

    def json(self):
        return self._json


@pytest.mark.parametrize('channel', (PhoneVerificationChannel.SMS, PhoneVerificationChannel.CALL))
@pytest.mark.django_db
def test_send_verification_code(channel, user_with_phone, mocker):
    mocked = mocker.patch.object(
        twilio_verify_api,
        'send_verification_code',
        return_value=MockResponse({'status': 'approved', 'sid': uuid4().hex})
    )
    send_verification_code.apply(
        kwargs=dict(
            phone_uuid=user_with_phone.profile.phone.uuid.hex,
            channel=channel.value,
            task_context={}
        )
    )
    mocked.assert_called_with(
        to=user_with_phone.profile.phone.number,
        channel=channel
    )


@pytest.mark.django_db
def test_check_verification_code(user_with_phone, mocker):
    mocked = mocker.patch.object(
        twilio_verify_api,
        'check_verification_code',
        return_value=MockResponse({'status': 'approved', 'sid': uuid4().hex})
    )
    verification_sid = uuid4().hex
    PhoneVerification.submit(
        sid=verification_sid,
        phone_id=user_with_phone.profile.phone.uuid,
        status=PhoneVerification.PENDING,
        task_id=uuid4()
    )
    pin = '123456'
    check_verification_code.apply(
        kwargs=dict(
            verification_sid=verification_sid,
            pin=pin,
            task_context={}
        )
    )
    mocked.assert_called_with(
        verification_sid=verification_sid,
        code=pin
    )
