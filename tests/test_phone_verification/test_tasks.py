from uuid import uuid4

import pytest
import requests_mock as rmock

from jibrel.authentication.enum import PhoneStatus
from jibrel.kyc.enum import PhoneVerificationStatus
from jibrel.kyc.tasks import (
    check_verification_code,
    send_verification_code
)
from jibrel.notifications.phone_verification import PhoneVerificationChannel


@pytest.mark.parametrize('channel', (PhoneVerificationChannel.SMS, PhoneVerificationChannel.CALL))
@pytest.mark.django_db
def test_send_verification_code(channel, user_with_phone, mocker, requests_mock):
    mocker.patch.object(send_verification_code, 'log_request_and_response')
    mocker.patch('jibrel.kyc.tasks.get_task_id', return_value=uuid4())
    requests_mock.post(rmock.ANY, json={'status': 'pending', 'sid': uuid4().hex})
    send_verification_code(
        phone_uuid=user_with_phone.profile.phone.uuid.hex,
        channel=channel.value,
        task_context={}
    )
    assert user_with_phone.profile.phone.status == PhoneStatus.CODE_SENT


@pytest.mark.parametrize(
    'twilio_status,expected_status',
    (
        (PhoneVerificationStatus.PENDING, PhoneStatus.CODE_INCORRECT),
        (PhoneVerificationStatus.EXPIRED, PhoneStatus.EXPIRED),
        (PhoneVerificationStatus.MAX_ATTEMPTS_REACHED, PhoneStatus.MAX_ATTEMPTS_REACHED),
        (PhoneVerificationStatus.APPROVED, PhoneStatus.VERIFIED),
    )
)
@pytest.mark.django_db
def test_check_verification_code(
    user_with_phone,
    mocker,
    requests_mock,
    verification_request_factory,
    twilio_status,
    expected_status,
):
    mocker.patch.object(check_verification_code, 'log_request_and_response')
    requests_mock.post(rmock.ANY, json={'status': twilio_status, 'sid': uuid4().hex})
    mocker.patch('jibrel.kyc.tasks.get_task_id', return_value=uuid4())
    mock = mocker.patch('jibrel.kyc.tasks.send_phone_verified_email')

    verification = verification_request_factory(
        user_with_phone.profile.phone,
        twilio_status
    )
    check_verification_code(
        verification_id=str(verification.pk),
        pin='123456',
        task_context={
            'user_id': uuid4().hex,
            'user_ip_address': '127.0.0.1,'
        }
    )
    assert user_with_phone.profile.phone.status == expected_status
    if expected_status == PhoneStatus.VERIFIED:
        mock.assert_called()


def test_two_users_verify_one_number(user_with_phone_factory, mocker, requests_mock):
    """Two different users sent same numbers at the same time"""
    mocker.patch.object(send_verification_code, 'log_request_and_response')
    mocker.patch('jibrel.kyc.tasks.get_task_id', return_value=uuid4())

    user1 = user_with_phone_factory()
    user2 = user_with_phone_factory()
    sid = uuid4().hex
    requests_mock.post(rmock.ANY, json={'status': PhoneVerificationStatus.PENDING, 'sid': sid})  # same sid for each user

    send_verification_code(
        phone_uuid=user1.profile.phone.uuid.hex,
        channel=PhoneVerificationChannel.SMS,
        task_context={}
    )

    send_verification_code(
        phone_uuid=user2.profile.phone.uuid.hex,
        channel=PhoneVerificationChannel.SMS,
        task_context={}
    )
