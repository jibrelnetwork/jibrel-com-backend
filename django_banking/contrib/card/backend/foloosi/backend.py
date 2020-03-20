import logging
from datetime import (
    datetime,
    timedelta
)
from decimal import Decimal
from typing import List
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property

from django_banking import logger
from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus


class FoloosiAPI:
    @cached_property
    def api(self):
        with requests.Session() as session:
            session.headers.update({
                'secret_key': settings.FOLOOSI_SECRET_KEY,
                'merchant_key': settings.FOLOOSI_MERCHANT_KEY
            })
            return session

    def _dispatch(self,
                  slug: str,
                  method: str,
                  data: [dict, str, None] = None):
        try:
            with self.api.request(
                    method=method,
                    url=urljoin(settings.FOLOOSI_API_URL, slug),
                    json=data,
                    timeout=60
                    ) as response:
                response.raise_for_status()
                body = response.json()
                data = body['data']
            return data
        except requests.exceptions.HTTPError:
            logger.log(
                level=logging.INFO,
                msg=f'Foloosi HTTP Error at {slug}'
            )
            return {}

    def request(self,
                customer: dict,
                amount: Decimal,
                optional: str = None,
                optional2: str = None,
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
            'optional1': optional,
            'optional2': optional2
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

    def list(self,
             from_date: datetime = None,
             page: int = None,
             limit: int = None
             ):
        """
        https://www.foloosi.com/api-document-v2

        """
        if from_date or page or limit:
            now = timezone.now()
            page = page or 1
            limit = limit or 100
            to_date = now.strftime('%m/%d/%Y')
            from_date = (from_date or (now - timedelta(settings.FOLOOSI_MAX_AGE_DEFAULT)).strftime('%m/%d/%Y'))
            query = f'{{"fromDate":"{from_date}","toDate":"{to_date}","page":"{page}","limit":"{limit}"}}'
            q = f'?q={query}' if query else ''
        else:
            q = ''
        return self._dispatch(
            slug=f'transaction-list{q}',
            method='GET',
        )['transactions']

    def all(self,
            from_date: datetime = None):
        page = 1
        limit = 100
        result = []
        while True:
            transactions = self.list(
                from_date=from_date,
                page=page,
                limit=limit
            )
            result.extend(transactions)

            if len(transactions) < limit:
                break
            page += 1
        return result

    def get_by_reference_code(self,
                              optional: str,
                              from_date: datetime = None,
                              exclude: List[str] = None):
        """
        https://www.foloosi.com/api-document-v2

        """
        exclude = set(exclude or {})
        page = 1
        limit = 100
        while True:
            transactions = self.list(
                from_date=from_date,
                page=page,
                limit=limit
            )
            for tx in transactions:
                if tx['transaction_no'] in exclude or tx['status'] != FoloosiStatus.CAPTURED:
                    continue
                data = self.get(tx['transaction_no'])
                if data.get('optional1') == optional:
                    return data

            if len(transactions) < limit:
                break
            page += 1

    def get(self, charge_id: str):
        """
        https://www.foloosi.com/api-document-v2

        """
        tx = self._dispatch(
            slug=f'transaction-detail/{charge_id}',
            method='GET',
        )
        if tx.get('status') == FoloosiStatus.CAPTURED:
            return tx
