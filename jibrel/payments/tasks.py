import logging
from decimal import Decimal
from uuid import UUID

import requests
from checkout_sdk.errors import (
    AuthenticationError,
    CheckoutSdkError,
    ResourceNotFoundError,
    TooManyRequestsError
)
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.urls import reverse

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI
from django_banking.contrib.card.backend.checkout.enum import CheckoutStatus
from django_banking.contrib.card.backend.checkout.models import (
    CheckoutCharge,
    UserCheckoutAccount
)
from django_banking.contrib.card.backend.checkout.signals import (
    charge_requested,
    charge_updated
)
from django_banking.contrib.card.models import DepositCardOperation
from jibrel.authentication.models import User
from jibrel.celery import app

logger = logging.getLogger(__name__)


@app.task(
    default_retry_delay=settings.CHECKOUT_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.CHECKOUT_MAX_RETIES,
)
def install_webhook():
    api = CheckoutAPI()
    url = f'http://{settings.DOMAIN_NAME}/{reverse("checkout-webhook")}'
    api.install_webhook(url)


@app.task(
    default_retry_delay=settings.CHECKOUT_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.CHECKOUT_MAX_RETIES,
)
@transaction.atomic
def checkout_update(charge_id: str, reference_code: str):
    """
    check current deposit id.
    Not necessary if webhooks is connected properly
    """
    deposit = DepositCardOperation.objects.get(
        references__reference_code=reference_code
    )
    try:
        api = CheckoutAPI()
        payment = api.get(charge_id=charge_id)
    except AuthenticationError as e:
        # TODO Handle 401
        # possible in case of manually check only
        # cannot do anything at that case actually. Sync issues possible
        raise e
    except ResourceNotFoundError as e:
        # TODO Handle 404
        raise e

    try:
        charge = CheckoutCharge.objects.get(charge_id=charge_id)
        charge.update_status(payment.status)
        charge.update_deposit_status()
    except ObjectDoesNotExist:
        # in case we lost data during creation
        # e.g. server shutdown or something like that
        charge = CheckoutCharge.objects.create(
            user=deposit.card_account.user,
            payment=payment,
            operation=deposit
        )
        charge.update_deposit_status()
    charge_updated.send(instance=charge, sender=charge.__class__)


@app.task(
    default_retry_delay=settings.CHECKOUT_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.CHECKOUT_MAX_RETIES,
)
@transaction.atomic
def checkout_request(deposit_id: UUID,
                     user_id: UUID,
                     token: str, amount: Decimal, reference: str):
    """
    deposit id is preferred above application_id as soon as
    deposit can be made independently
    """
    api = CheckoutAPI()
    deposit = DepositCardOperation.objects.get(
        pk=deposit_id
    )
    user = User.objects.get(
        pk=user_id
    )
    kyc = user.profile.last_kyc.details
    email = getattr(kyc, 'email', user.email)
    try:
        user_checkout_account = UserCheckoutAccount.objects.get(user=user)
        customer = {
            'id': user_checkout_account.customer_id
        }
    except ObjectDoesNotExist:
        customer = {
            'email': email,
            'name': str(kyc)
        }

    try:
        payment = api.request_from_token(
            customer=customer,
            token=token,
            amount=amount,
            reference=reference
        )
    except TooManyRequestsError as e:
        # TODO handle 429 by webhook
        # it means that we lost transaction id
        logger.log(
            level=logging.ERROR,
            msg=f'Lost payment id: {e.error_type} {reference}. Please wait webhook now.'
        )
    except CheckoutSdkError:
        deposit.status = CheckoutCharge.get_deposit_status(CheckoutStatus.DECLINED)
        deposit.save(update_fields=['status'])

    else:
        charge = CheckoutCharge.objects.create(
            user=user,
            payment=payment,
            operation=deposit
        )
        charge.update_deposit_status()
        charge_requested.send(instance=charge, sender=charge.__class__)
