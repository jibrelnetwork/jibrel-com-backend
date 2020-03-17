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
from django_banking.contrib.card.backend.checkout.models import (
    CheckoutCharge,
    UserCheckoutAccount
)
from django_banking.contrib.card.backend.checkout.signals import (
    checkout_charge_requested,
    checkout_charge_updated
)
from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI
from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge
from django_banking.contrib.card.backend.foloosi.signals import (
    foloosi_charge_requested,
    foloosi_charge_updated
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
    # TODO change webhook url dynamically
    api = CheckoutAPI()
    url = f'{settings.WEBHOOK_ROOT}/{reverse("checkout-webhook")}'
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
            user=deposit.user,
            payment=payment,
            operation=deposit
        )
        charge.update_deposit_status()
    checkout_charge_updated.send(instance=charge, sender=charge.__class__)


@app.task(
    default_retry_delay=settings.CHECKOUT_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.CHECKOUT_MAX_RETIES,
)
@transaction.atomic
def checkout_request(deposit_id: UUID,
                     user_id: UUID,
                     amount: Decimal,
                     reference_code: str,
                     checkout_token: str,
                     **kwargs):
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
            token=checkout_token,
            amount=amount,
            reference=reference_code
        )
    except TooManyRequestsError as e:
        # it means that we lost transaction id
        logger.log(
            level=logging.ERROR,
            msg=f'Lost payment id: {e.error_type} {reference_code}. Please wait webhook now.'
        )
    except CheckoutSdkError as e:
        logger.log(
            level=logging.ERROR,
            msg=f'Something went wrong: {e.error_type} {reference_code}.'
        )
        deposit.cancel()

    else:
        charge = CheckoutCharge.objects.create(
            user=user,
            payment=payment,
            operation=deposit
        )
        charge.update_deposit_status()
        checkout_charge_requested.send(instance=charge, sender=charge.__class__)


@app.task(
    default_retry_delay=settings.FOLOOSI_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.FOLOOSI_MAX_RETIES,
)
@transaction.atomic
def foloosi_update(reference_code: str):
    """
    check current deposit id.
    Not necessary if webhooks is connected properly
    """
    deposit = DepositCardOperation.objects.filter(
        references__reference_code=reference_code
    ).latest('created_at')
    # to ensure it is foloosi charge
    try:
        charge = deposit.charge_foloosi.latest('updated_at')
    except ObjectDoesNotExist:
        logger.log(
            level=logging.ERROR,
            msg=f'Wrong backend. Not A Foloosi charge: {reference_code}.'
        )
        return
    api = FoloosiAPI()
    if charge.charge_id:
        # actually not possible. just in case
        payment = api.get(charge_id=charge.charge_id)
    else:
        exclude = FoloosiCharge.objects.filter(
            created_at__gte=charge.created_at,
            charge_id__isnull=False
        ).values_list('charge_id', flat=True)
        payment = api.get_by_reference_code(
            optional=str(deposit.pk),
            from_date=charge.created_at,
            exclude=exclude
        )
    if not payment:
        return
    charge.charge_id = payment['transaction_no']
    charge.update_status(payment['status'])
    charge.update_deposit_status()
    foloosi_charge_updated.send(instance=charge, sender=charge.__class__)


@app.task(
    default_retry_delay=settings.FOLOOSI_SCHEDULE,
    autoretry_for=(requests.exceptions.HTTPError,),
    max_retries=settings.FOLOOSI_MAX_RETIES,
)
@transaction.atomic
def foloosi_update_all():
    try:
        from_date = FoloosiCharge.objects.filter(
            charge_id__isnull=True
        ).earliest('created_at').created_at
    except ObjectDoesNotExist:
        return

    exclude = FoloosiCharge.objects.filter(
        created_at__gte=from_date,
        charge_id__isnull=False
    ).values_list('charge_id', flat=True)

    # to ensure it is foloosi charge
    api = FoloosiAPI()
    payments = api.all(
        from_date=from_date,
        exclude=exclude
    )
    for payment in payments:
        deposit_id = payment.get('optional1', None)
        if not deposit_id:
            continue
        charge = FoloosiCharge.objects.filter(
            operation=deposit_id
        ).first()
        if not charge:
            continue
        charge.charge_id = payment['transaction_no']
        charge.update_status(payment['status'])
        charge.update_deposit_status()
        foloosi_charge_updated.send(instance=charge, sender=charge.__class__)


@app.task(
    default_retry_delay=settings.FOLOOSI_SCHEDULE,
    autoretry_for=(requests.exceptions.RequestException,),
    max_retries=settings.FOLOOSI_MAX_RETIES,
)
@transaction.atomic
def foloosi_request(deposit_id: UUID,
                    user_id: UUID,
                    amount: Decimal,
                    reference_code: str,
                    **kwargs):
    api = FoloosiAPI()
    deposit = DepositCardOperation.objects.get(
        pk=deposit_id
    )
    user = User.objects.get(
        pk=user_id
    )
    kyc = user.profile.last_kyc.details
    email = getattr(kyc, 'email', user.email)
    customer = {
        'email': email,
        'name': str(kyc),
        'mobile': user.profile.phone.number,
        'address': kyc.address,
        'city': kyc.city,
    }
    try:
        payment = api.request(
            customer=customer,
            amount=amount,
            optional=str(deposit_id),
            optional2=reference_code,
            redirect_url=''  # todo
        )
    except requests.exceptions.RequestException as e:
        raise e
    except Exception as e:
        logger.log(
            level=logging.ERROR,
            msg=f'Something went wrong: {str(e)} {reference_code}.'
        )
        deposit.cancel()
        raise e

    else:
        charge = FoloosiCharge.objects.create(
            user=user,
            payment=payment,
            operation=deposit
        )
        charge.update_deposit_status()
        foloosi_charge_requested.send(instance=charge, sender=charge.__class__)


def card_charge_request(**kwargs):
    task = {
        'django_banking.contrib.card.backend.checkout': checkout_request,
        'django_banking.contrib.card.backend.foloosi': foloosi_request,
    }[settings.DJANGO_BANKING_CARD_BACKEND]
    task.delay(**kwargs)
