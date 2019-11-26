from datetime import timedelta

import pytest
from django.utils import timezone

from jibrel.notifications.models import ExternalServiceCallLog
from tests.fixtures import DEFAULT_ACTION_TYPE


@pytest.mark.django_db
def test_external_call_was_request_in(external_call_log, mocker):
    seconds = 60
    now = timezone.now()
    past = now - timedelta(seconds=seconds)
    future = now + timedelta(seconds=seconds)

    external_call_log.created_at = past
    external_call_log.save()

    mocked_now = mocker.patch('django.utils.timezone.now')
    mocked_now.return_value = future

    assert not ExternalServiceCallLog.was_request_in(external_call_log.initiator.uuid, DEFAULT_ACTION_TYPE, seconds)

    mocked_now.return_value = now

    assert ExternalServiceCallLog.was_request_in(external_call_log.initiator.uuid, DEFAULT_ACTION_TYPE, seconds)

    mocked_now.return_value = past

    assert ExternalServiceCallLog.was_request_in(external_call_log.initiator.uuid, DEFAULT_ACTION_TYPE, seconds)
