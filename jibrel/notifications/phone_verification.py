from enum import Enum
from typing import Any

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth


class PhoneVerificationChannel(Enum):
    SMS = 'sms'
    CALL = 'call'


class TwilioVerifyAPI:
    def __init__(
        self,
        account_sid: str,
        secret_key: str,
        service_sid: str,
    ):
        self._auth = HTTPBasicAuth(account_sid, secret_key)
        self._base_url = f'{settings.TWILIO_API_URL}/Services/{service_sid}'

    def _send_request(
        self,
        method: str,
        path: str,
        **kwargs: Any
    ) -> requests.Response:
        return requests.request(
            method,
            f'{self._base_url}{path}',
            auth=self._auth,
            timeout=settings.TWILIO_REQUEST_TIMEOUT,
            **kwargs
        )

    def send_verification_code(
        self,
        to: str,
        channel: PhoneVerificationChannel,
    ) -> requests.Response:
        url = '/Verifications'
        return self._send_request('POST', url, data={'To': to, 'Channel': channel.value})

    def check_verification_code(
        self,
        verification_sid: str,
        code: str,
    ) -> requests.Response:
        url = '/VerificationCheck'
        return self._send_request('POST', url, data={'VerificationSid': verification_sid, 'Code': code})
