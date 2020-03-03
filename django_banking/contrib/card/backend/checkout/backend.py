import logging
from decimal import Decimal

from checkout_sdk import HTTPMethod
from checkout_sdk.errors import CheckoutSdkError
from django.conf import settings
from django.utils.functional import cached_property

from django_banking.contrib.card.backend.checkout import logger
import checkout_sdk as sdk


class CheckoutAPI:
    @cached_property
    def api(self):
        return sdk.get_api(secret_key=settings.CHECKOUT_PRIVATE_KEY,
                           sandbox=settings.CHECKOUT_SANDBOX)

    @cached_property
    def public_api(self):
        print(settings.CHECKOUT_PUBLIC_KEY)
        return sdk.get_api(secret_key=settings.CHECKOUT_PUBLIC_KEY,
                           sandbox=settings.CHECKOUT_SANDBOX)

    def _dispatch(self, method: str, data: [dict, str]):
        try:
            return getattr(self.api.payments, method)(data)
        except CheckoutSdkError as e:
            logger.log(
                level=logging.ERROR,
                msg=f'{e.http_status} {e.error_type} {e.elapsed} {e.request_id}'
            )
            raise e

        # # check if payment does not required 3ds
        # if payment.is_pending:
        #     return {
        #         'success': True,
        #         'status': payment.status,
        #         'charge_id': payment.id
        #     }
        #
        # # if payment.__dict__['3ds'].downgraded:
        # if payment.requires_redirect:
        #     return {
        #         'success': True,
        #         'status': payment.status,
        #         'payment_id': payment.id,
        #         'redirect_link': payment.redirect_link
        #     }

    def request_from_token(self, customer: dict, amount: Decimal, token: str):
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
                # threeds={
                #     'enabled': True,
                #     'attempt_n3d': True
                # },

                'risk': {
                    'enabled': True
                },
                'threeds': {
                    'enabled': True,
                    'attempt_n3d': True
                },

                'amount': int(amount * 100),  # cents
                'currency': sdk.Currency.USD
                # 'capture': True,
                # 'customer': customer
           }
        )

    def request_from_card(self, customer: dict, amount: Decimal,
                          number: int,  expiry_month: int,  expiry_year: str,  cvv: str):
        """
        https://api-reference.checkout.com/#tag/Payments/paths/~1payments/post

        """

        return self._dispatch(
            'request',
            {
                'source': {
                    'type': 'card',
                    'number': number,
                    'expiry_month': int(expiry_month),
                    'expiry_year': int(expiry_year),
                    'cvv': cvv
                },
                'risk': {
                    'enabled': True
                },
                '3ds': {
                    'enabled': False
                },
                # threeds={
                #     'enabled': True,
                #     'attempt_n3d': True
                # },
                'amount': int(amount * 100),  # cents
                'currency': sdk.Currency.USD,
                # capture=True,
                # customer=customer
            }
        )

    def tokenize(self, **kwargs):
        """
        https://api-reference.checkout.com/#tag/Tokens/paths/~1tokens/post
        tokens are not supported by SDK
        workaround is here
        """
        if {'number', 'expiry_month', 'expiry_year'} - set(kwargs.keys()):
            raise Exception('Missing required parameters')
        return self.public_api.payments._send_http_request(
            'tokens', HTTPMethod.POST, dict(
                type='card',
                **kwargs
            ))

    def get(self, charge_id: str):
        return self._dispatch('get', charge_id)
