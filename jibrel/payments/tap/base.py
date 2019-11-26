"""Tap client.

TODO: handle deserialization errors
"""
import logging
from collections import UserList
from enum import Enum
from json import JSONDecodeError
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from dataclasses_json import dataclass_json

from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass
class Phone:
    country_code: str = None
    number: str = None


@dataclass_json
@dataclass
class Card:

    id: str
    customer: str
    exp_month: int = None
    exp_year: int = None
    last_four: str = None
    name: str = None
    brand: str = None


@dataclass_json
@dataclass
class TapCustomer:

    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[Phone] = None
    currency: Optional[str] = None
    metadata: Optional[Dict] = None


class ChargeStatus(Enum):
    INITIATED = 'INITIATED'
    ABANDONED = 'ABANDONED'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'
    DECLINED = 'DECLINED'
    RESTRICTED = 'RESTRICTED'
    CAPTURED = 'CAPTURED'
    VOID = 'VOID'
    TIMEDOUT = 'TIMEDOUT'
    UNKNOWN = 'UNKNOWN'


@dataclass_json
@dataclass
class Transaction:

    """Charge transaction info.

    Part of charge response. Only url important for a while.
    """

    url: Optional[str] = None


@dataclass_json
@dataclass
class ChargeSource:

    """Charge source.

    Charge source may vary, including token sources etc. Nested parted of charge
    response.
    """

    id: str


@dataclass_json
@dataclass
class Charge:

    """Tap charge.
    """

    id: str
    status: ChargeStatus
    amount: float
    currency: str
    threeDSecure: bool
    save_card: bool
    customer: TapCustomer
    transaction: Transaction
    source: ChargeSource


class ListResponseMixIn:

    """Tap list response mixin.

    Contains additional metadata from response instead of plain object list.
    """
    has_more: bool = False

    def __init__(self, initlist, has_more=False):
        self.has_more = has_more
        super().__init__(initlist)


class ChargeListResponse(ListResponseMixIn, UserList):
    data: List[Charge]


class CardListResponse(ListResponseMixIn, UserList):
    data: List[Card]


@dataclass_json
@dataclass
class Token:

    """Tap token.
    """

    id: str
    card: Card


class TapException(Exception):
    pass


class TapClientException(TapException):
    pass


class InvalidChargeId(TapClientException):
    pass


class ChargeNotFound(InvalidChargeId):
    pass


class InvalidCardId(TapClientException):
    pass


class CardNotFound(InvalidCardId):
    pass


class InvalidCustomer(TapClientException):
    pass


class InvalidCustomerId(InvalidCustomer):
    pass


class CustomerNotFound(InvalidCustomerId):
    pass


class PhoneOrEmailRequired(InvalidCustomer):
    pass


class InvalidToken(TapClientException):
    pass


class TapClient:

    """Tap rest api client.

    Should be used with context only:

        with TapClient(...) as client:
            client.create_customer(...)

    TODO: add API version compatibility check
    """

    base_url = 'https://api.tap.company/v2/'

    error_code_map = {
        'invalid_customer_id': InvalidCustomerId,
        'card_not_found': CardNotFound,
        'record_not_found': InvalidToken,  # TODO

        '1104': InvalidCustomerId,
        '1105': InvalidCustomerId,
        '1106': CustomerNotFound,
        '1107': CustomerNotFound,

        '1130': InvalidCustomer,
        '1139': PhoneOrEmailRequired,

        '1143': InvalidChargeId,
        '1144': ChargeNotFound,
    }

    _session: requests.Session

    def __init__(self, secret, pub, enc_key):
        self._secret = secret
        self._pub = pub
        self._enc_key = enc_key

        self._customers_cache = {}

    def get_customer(self, customer_id: str) -> TapCustomer:
        """Get customer info.

        :param customer_id: tap customer id
        :raise CustomerNotFound: if customer with such id didn't found
        :raise InvalidCustomerId: if customer id is invalid or not found
        :raise HttpError: if unpredicted error code returned from tap
        """
        if not isinstance(customer_id, str):
            raise InvalidCustomerId()

        if customer_id in self._customers_cache:
            return self._customers_cache[customer_id]

        obj = TapCustomer.from_dict(self._get(f'customers/{customer_id}'))

        self._customers_cache[obj.id] = obj

        return obj

    def create_customer(self, first_name, last_name, email, phone: Phone, currency=None) -> TapCustomer:
        """Create tap customer.

        :raise TapClientException: in case of invalid data
        :raise HttpError: if unpredicted error code returned from tap
        """
        customer_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': {
                'country_code': phone.country_code,
                'number': phone.number
            },
            'currency': currency
        }
        logger.debug("Create tap customer with request body: %s", customer_data)

        data = self._post('customers', customer_data)
        customer = TapCustomer.from_dict(data)

        self._customers_cache[customer.id] = customer
        return customer

    def get_card_list(self, customer_id: str, starting_after=None) -> CardListResponse:
        """Get tap customers saved cards.

        :raise CustomerNotFound: if customer with such id didn't found
        :raise InvalidCustomerId: if customer id is invalid or not found
        :raise HttpError: if unpredicted error code returned from tap
        """
        resp = self._get(f'card/{customer_id}', {
            'starting_after': starting_after
        })
        cards_list = [
            Card.from_dict(card_data) for card_data in resp['data']
        ]
        result = CardListResponse(cards_list, has_more=resp['has_more'])
        return result

    def get_card(self, customer_id: str, card_id: str):
        data = self._get(f'card/{customer_id}/{card_id}')
        return Card.from_dict(data)

    def create_charge(self,
                      customer_id: str,
                      amount: float,
                      currency: str,
                      redirect_url: str,
                      card_id: str = None) -> Charge:
        """Create charge.

        :raise CustomerNotFound: if customer with such id didn't found
        :raise InvalidCustomerId: if customer id is invalid or not found
        :raise CardNotFound: if provided card id invalid or didn't found
        :raise HttpError: if unpredicted error code returned from tap
        """
        source_id = 'src_card'
        if card_id:
            token = self.create_token(customer_id, card_id)
            source_id = token.id

        charge_data = {
            "customer": {
                "id": customer_id
            },
            "source": {
                "id": source_id
            },
            "amount": amount,
            "currency": currency,
            "redirect": {
                "url": redirect_url
            }
        }

        return Charge.from_dict(self._post('charges', json=charge_data))

    def get_charge(self, charge_id: str) -> Charge:
        """Get charge info by id.

        :raise InvalidChargeId:
        :raise ChargeNotFound:
        :raise HttpError: if unpredicted error code returned from tap
        """
        return Charge.from_dict(self._get(f'charges/{charge_id}'))

    def get_charge_list(self, starting_after: str = None) -> ChargeListResponse:
        """Get charges list.

        Return all available charges. You can use last received charge id
        for `starting_after` in next request to get next results page.

        :param starting_after:
        :raise HttpError: if unpredicted error code returned from tap
        """
        resp = self._post('charges/list', {
            'starting_after': starting_after
        })
        return ChargeListResponse([
            Charge.from_dict(charge_data)
            for charge_data in resp['charges']
        ], has_more=resp['has_more'])

    def create_token(self, customer_id: str, card_id: str) -> Token:
        """Get one-time token for saved card.

        :raise CustomerNotFound: if customer with such id didn't found
        :raise InvalidCustomerId: if customer id is invalid or not found
        :raise CardNotFound: if provided card id invalid or didn't found
        :raise HttpError: if unpredicted error code returned from tap
        """
        token_data = self._post('tokens', {
            'saved_card': {
                'card_id': card_id,
                'customer_id': customer_id
            }
        })
        return Token.from_dict(token_data)

    def get_token(self, token_id: str):
        """Retrieve existing token info.

        :raise HttpError: if unpredicted error code returned from tap
        """
        token_data = self._get(f'tokens/{token_id}')
        return Token.from_dict(token_data)

    def _get(self, endpoint, params=None, filter_empty=True):
        assert getattr(self, '_session', None) is not None, \
            "TapClient should be used as contextmanager"
        url = urljoin(self.base_url, endpoint)
        if params and filter_empty:
            params = {k: v for k, v in params.items()}
        resp = self._session.get(
            url,
            params=params
        )
        logger.debug("Tap GET %s params: `%s` response %i: `%s`",
                     url, params, resp.status_code, resp.content)

        self._handle_error_codes(resp)

        return resp.json()

    def _post(self, endpoint, json=None, filter_empty=True):
        assert getattr(self, '_session', None) is not None, \
            "TapClient should be used as contextmanager"
        url = urljoin(self.base_url, endpoint)
        if json and filter_empty:
            json = {k: v for k, v in json.items() if v}
        resp = self._session.post(
            url,
            json=json
        )
        logger.debug("Tap POST %s request: `%s` response %i: `%s`",
                     url, json, resp.status_code, resp.content)

        self._handle_error_codes(resp)

        return resp.json()

    def _handle_error_codes(self, resp):
        if resp.status_code in (400, 404):  # there is 404 for token endpoint
            try:
                data = resp.json()

                if 'status' in data and 'type' in data:
                    # Special case for charge errors
                    error_type = data['type']
                    if error_type in self.error_code_map:
                        raise self.error_code_map[error_type]()

                if 'errors' in data:
                    for error in data['errors']:
                        code = error.get('code')
                        exc_cls = self.error_code_map.get(code)
                        if exc_cls:
                            raise exc_cls(error)
            except JSONDecodeError:
                logger.error("Error while parsing json response from tap: %s",
                             resp.content)

        resp.raise_for_status()

    def __enter__(self):
        self._session = requests.Session()
        self._session.headers['Authorization'] = f'Bearer {self._secret}'
        self._session.headers['Content-type'] = 'application/json'
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()


def get_tap_client():
    return TapClient(settings.TAP_SECRET, settings.TAP_PUB, settings.TAP_KEY)
