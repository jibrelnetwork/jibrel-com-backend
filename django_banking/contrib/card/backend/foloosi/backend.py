from datetime import (
    datetime,
    timedelta
)
from decimal import Decimal
from operator import itemgetter
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property

from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge


class FoloosiAPI:
    @cached_property
    def api(self):
        session = requests.Session()
        print(settings.FOLOOSI_SECRET_KEY)
        print(settings.FOLOOSI_MERCHANT_KEY)
        print(settings.FOLOOSI_SECRET_KEY == 'test_$2y$10$dfKAqPxbZsv8Qx37xZ3g6eAJv4gHMCXhqunwr9GRArZO54fwgZKLO')
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
        with api.request(
            method=method,
            url=urljoin('https://foloosi.com/api/v1/api/', slug),
            json=data,
            timeout=60
        ) as response:
            response.raise_for_status()
            body = response.json()
            data = body['data']
            return data

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
            'optional1': reference
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

    def list(self, query=None):
        """
        https://www.foloosi.com/api-document-v2

        """
        q = f'?q={query}' if query else ''
        return self._dispatch(
            slug=f'transaction-list{q}',
            method='GET',
        )['transactions']

    def get_by_reference_code(self, reference_code: str, from_date: datetime = None):
        """
        https://www.foloosi.com/api-document-v2

        """
        now = timezone.now()
        to_date = now.strftime('%m/%d/%Y')
        from_date = (from_date or (now - timedelta(5)).strftime('%m/%d/%Y'))
        transaction = None
        page = 1
        limit = 100
        # TODO. this is not an efficient way. Should be rewritten
        while not transaction:
            transactions = self.list(f'{{"fromDate":"{from_date}","toDate":"{to_date}","page":"{page}","limit":"{limit}"}}')
            if len(transactions) == 0:
                break

            exclude = FoloosiCharge.objects.filter(
                charge_id__in=map(itemgetter('transaction_no'), transactions)
            ).values_list('charge_id', flat=True)

            for tx in transactions:
                if tx['transaction_no'] in exclude:
                    continue
                data = self.get(tx['transaction_no'])
                if data.get('optional1') == reference_code:
                    transaction = data
                    break
            if len(transactions) < 100:
                break
            page += 1
        return transaction

    def get(self, charge_id: str):
        """
        https://www.foloosi.com/api-document-v2

        """
        return self._dispatch(
            slug=f'transaction-detail/{charge_id}',
            method='GET',
        )
