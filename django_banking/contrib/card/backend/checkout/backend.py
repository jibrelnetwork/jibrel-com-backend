import logging
from decimal import Decimal

import checkout_sdk as sdk
from checkout_sdk import HTTPMethod
from checkout_sdk.errors import CheckoutSdkError
from django.conf import settings
from django.utils.functional import cached_property

from django_banking.contrib.card.backend.checkout import logger


class CheckoutAPI:
    @cached_property
    def api(self):
        return sdk.get_api(
            secret_key=settings.CHECKOUT_PRIVATE_KEY,
            sandbox=settings.CHECKOUT_SANDBOX
        )

    @cached_property
    def public_api(self):
        if not settings.DEBUG:
            raise Exception('Does not allowed at production environment')
        return sdk.get_api(
            secret_key=settings.CHECKOUT_PUBLIC_KEY,
            sandbox=settings.CHECKOUT_SANDBOX
        )

    def _dispatch(self, method: str, data: [dict, str]):
        try:
            return getattr(self.api.payments, method)(data)
        except CheckoutSdkError as e:
            logger.log(
                level=logging.ERROR,
                msg=f'{e.http_status} {e.error_type} {e.elapsed} {e.request_id}'
            )
            raise e

    def request_from_token(self, customer: dict, amount: Decimal, token: str, reference: str = None):
        """
        https://api-reference.checkout.com/#tag/Payments/paths/~1payments/post

        """
        return self._dispatch(
            'request',
           {
                'source':{
                    "type": "token",
                    "token": token
                },
                'risk': {
                    'enabled': True
                },
                'threeds': {
                    'enabled': True,
                    'attempt_n3d': True
                },

                'amount': int(amount * 100),  # cents
                'currency': sdk.Currency.USD,
                'capture': True,
                'customer': customer,
                'reference': reference
           }
        )

    def get(self, charge_id: str):
        return self._dispatch('get', charge_id)

    def tokenize(self, **kwargs):
        """
        https://api-reference.checkout.com/#tag/Tokens/paths/~1tokens/post
        tokens are not supported by SDK. Public keys is not supported also
        """
        if {'number', 'expiry_month', 'expiry_year'} - set(kwargs.keys()):
            raise Exception('Missing required parameters')
        return self.public_api.payments._send_http_request(
            'tokens', HTTPMethod.POST, dict(
                type='card',
                **kwargs
            ))

    def install_webhook(self, url):
        return self.api.payments._send_http_request(
            'webhooks', HTTPMethod.POST, {
                "url": url,
                "content_type": "json",
                "event_types": [
                    "payment_approved",
                    "payment_pending",
                    "payment_declined",
                    "payment_expired",
                    "payment_canceled",
                    "payment_voided",
                    "payment_captured",
                    "payment_refunded",
                    "payment_paid"
                ]
            })

    def retry_webhook(self, webhook_id, event_id):
        return self.api.payments._send_http_request(
            f'events/{event_id}/webhooks/{webhook_id}/retry', HTTPMethod.POST
        )
