import logging
from decimal import Decimal
from uuid import UUID

import requests
from checkout_sdk.errors import (
    CheckoutSdkError,
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
def checkout_get(deposit_id: UUID):
    """
    check current deposit id.
    Not necessary if webhooks is connected properly
    """
    api = CheckoutAPI()
    try:
        charge = CheckoutCharge.objects.filter(
            operation_id=deposit_id
        )
    except ObjectDoesNotExist:
        logger.log(
            level=logging.ERROR,
            msg=f'Charge does not exist: {deposit_id}'
        )
        return

    try:
        payment = api.get(
            charge_id=charge.charge_id,
        )
    except CheckoutSdkError:
        charge.update_status(CheckoutStatus.DECLINED)
    else:
        charge.update_status(payment.status)
    finally:
        charge_updated(charge, sender=charge.__class__)


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
    # asset = Asset.objects.main_fiat_for_customer(user)
    kyc = user.profile.last_kyc.details
    email = getattr(kyc, 'email', user.email)
    # check already existing customer
    # create the new one otherwise
    user_checkout_account = None
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
        charge_requested(charge, sender=charge.__class__)



    # deposit.s
    #
    # if
    # application = InvestmentApplication.objects.with_draft().filter(
    #     deposit_id=deposit_id,
    #     status=InvestmentApplicationStatus.DRAFT,
    #     subscription_agreement_status=InvestmentApplicationAgreementStatus.INITIAL,
    # ).first()
    # if not application:
    #     logger.warning('Draft application with Initial agreement status with id %s was not found', application_id)
    #     return
