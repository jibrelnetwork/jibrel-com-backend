import logging

from django.conf import settings
from requests import HTTPError

from jibrel.authentication.models import User
from jibrel.celery import app
from jibrel.core.errors import CoinMENAException
from jibrel.notifications.email import (
    FiatDepositApprovedEmailMessage,
    FiatDepositRejectedEmailMessage,
    FiatWithdrawalApprovedEmailMessage,
    FiatWithdrawalRejectedEmailMessage
)
from jibrel.notifications.tasks import send_mail
from jibrel.payments.tap import process_tap_charge
from jibrel.accounting.models import Operation
from jibrel.payments.tap import Charge, ChargeStatus, get_tap_client

logger = logging.getLogger(__name__)


@app.task()
def send_fiat_withdrawal_approved_mail(user_id):
    user = User.objects.select_related('profile').get(pk=user_id)
    rendered = FiatWithdrawalApprovedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_fiat_withdrawal_rejected_mail(user_id, operation_id):
    user = User.objects.select_related('profile').get(pk=user_id)
    operation = Operation.objects.with_amounts(user).get(pk=operation_id)
    rendered = FiatWithdrawalRejectedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username,
        'amount': f'{operation.credit_amount} {operation.credit_asset}',
        'sign_in_link': settings.APP_SIGN_IN_LINK.format(email=user.email),
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_fiat_deposit_approved_mail(user_id):
    user = User.objects.select_related('profile').get(pk=user_id)
    rendered = FiatDepositApprovedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task()
def send_fiat_deposit_rejected_mail(user_id):
    user = User.objects.select_related('profile').get(pk=user_id)
    rendered = FiatDepositRejectedEmailMessage.translate(user.profile.language).render({
        'name': user.profile.username,
    })
    send_mail.delay(
        recipient=user.email,
        task_context={},
        **rendered.serialize()
    )


@app.task(bind=True, retry_backoff=5, autoretry_for=(HTTPError,))
def process_charge(self, charge):
    charge = Charge.from_dict(charge)
    # TODO: handle special sources `src_kw.knet` etc
    try:
        customer = User.objects.get(profile__tap_customer_id=charge.customer.id)
    except User.DoesNotExist:
        # TODO: replace with error for real account (only)
        logger.debug("Skip charge %s because customer id %s didn't "
                     "match any customer in our database",
                     charge, charge.customer.id)
        return

    with get_tap_client() as client:
        charge_token = client.get_token(charge.source.id)

        card = client.get_card(charge.customer.id, charge_token.card.id)

        try:
            process_tap_charge(customer, charge, card)
        except CoinMENAException:
            logger.exception("Charge %s processing exception (skip)", charge)
            return

        if charge.status == ChargeStatus.INITIATED:
            logger.info("Retry processing of INITIATED charge %s", charge)
            raise self.retry()


@app.task(expires=settings.TAP_CHARGE_PROCESSING_SCHEDULE)
def fetch_charges():
    """Fetch all charges from tap and process them.
    """
    max_depth = 4
    starting_after = None

    with get_tap_client() as client:
        for i in range(max_depth):
            charges = client.get_charge_list(starting_after=starting_after)

            for charge in charges:
                process_charge.delay(charge.to_dict())
                starting_after = charge.id

            if not charges.has_more:
                break
