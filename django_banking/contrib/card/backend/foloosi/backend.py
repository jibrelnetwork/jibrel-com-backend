from decimal import Decimal
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils.functional import cached_property


class FoloosiAPI:
    @cached_property
    def api(self):
        session = requests.Session()
        session.headers.update({
            'secret_key': settings.FOLOOSI_SECRET_KEY,
            'merchant_key': settings.FOLOOSI_MERCHANT_KEY
        })
        return session

    def _dispatch(self,
                  slug: str,
                  method: str,
                  data: [dict, str, None] = None,
                  api: requests.Session = None):
        api = api or self.api
        response = api.request(
            method=method,
            url=urljoin('https://foloosi.com/api/v1/api/', slug),
            json=data,
            timeout=60,
            headers={
                'secret_key': settings.FOLOOSI_SECRET_KEY,
                'merchant_key': settings.FOLOOSI_MERCHANT_KEY
            }
        )
        response.raise_for_status()
        body = response.json()
        return body

    def request(self,
                customer: dict,
                amount: Decimal,
                reference: [str, None] = None,
                redirect_url: str = ''):
        """
        https://www.foloosi.com/api-document-v2

        """
        deposit_data = {k: v for k, v in {
            'customer_name': customer.get('name',),
            'customer_email': customer.get('email'),
            'customer_mobile': customer.get('mobile'),
            'customer_address': customer.get('address'),
            'customer_city': customer.get('city'),
            'reference': reference
        }.items() if v is not None}

        return self._dispatch(
            slug='initialize-setup',
            method='POST',
            data={
                'redirect_url': redirect_url,
                'transaction_amount': str(Decimal(amount)),
                'currency': 'USD',
                **deposit_data
            }
        )

    def list(self):
        """
        https://www.foloosi.com/api-document-v2

        """
        return self._dispatch(
            slug=f'transaction-list?status=123',
            method='GET',
        )

    def get_by_reference_code(self, reference_code: str):
        """
        https://www.foloosi.com/api-document-v2

        """
        return self.list()

    def get(self, charge_id: str):
        """
        https://www.foloosi.com/api-document-v2

        """
        return self._dispatch(
            slug=f'transaction-detail/{charge_id}',
            method='GET',
        )
