from uuid import uuid4

import pytest

from jibrel.kyc.models import PhoneVerification


@pytest.fixture
def verification_request_factory():
    def _verification_request_factory(phone, status):
        return PhoneVerification.objects.create(
            verification_sid=uuid4().hex,
            phone=phone,
            status=status,
        )
    return _verification_request_factory
