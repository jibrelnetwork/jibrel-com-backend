from uuid import uuid4

import pytest

from jibrel.kyc.models import PhoneVerification


@pytest.mark.django_db
def test_phone_verification_submit(user_with_phone):
    task1_uuid = uuid4()
    task2_uuid = uuid4()
    sid = 'sid'
    verification = PhoneVerification.submit(
        sid=sid,
        phone_id=user_with_phone.profile.phone.uuid,
        task_id=task1_uuid,
        status=PhoneVerification.PENDING,
    )
    assert verification.status == PhoneVerification.PENDING
    assert len(verification.task_ids) == 1
    assert verification.task_ids[0] == task1_uuid

    verification2 = PhoneVerification.submit(
        sid=sid,
        phone_id=user_with_phone.profile.phone.uuid,
        task_id=task2_uuid,
        status=PhoneVerification.APPROVED,
    )

    assert verification == verification2
    assert verification2.status == PhoneVerification.APPROVED
    assert len(verification2.task_ids) == 2
    assert verification2.task_ids[0] == task1_uuid
    assert verification2.task_ids[1] == task2_uuid
