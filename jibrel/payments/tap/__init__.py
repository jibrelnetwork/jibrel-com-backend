import logging
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from jibrel.accounting.models import Account, Asset, Operation
from jibrel.authentication.models import Profile
from jibrel.core.errors import CoinMENAException
from jibrel.payments.fees import calculate_fee_card_deposit
from jibrel.payments.models import (
    CardAccount,
    FeeUserAccount,
    RoundingUserAccount,
    TapCharge,
    UserAccount
)

from .base import Card, Charge, ChargeStatus, Phone, get_tap_client

logger = logging.getLogger(__name__)


@dataclass
class TapOperationAccounts:
    """Accounts required for tap operation.
    """
    card_account: Account
    user_account: Account
    fee_account: Account
    rounding_account: Account


def get_tap_deposit_operation_accounts(user, asset, card_id) -> TapOperationAccounts:
    with transaction.atomic():
        plastic_card_account, created = CardAccount.objects.get_or_create(
            user=user,
            asset=asset,
            tap_card_id=card_id,
        )
        user_account = UserAccount.objects.for_customer(user, asset)
        fee_account = FeeUserAccount.objects.for_customer(user=user,
                                                          asset=user_account.asset)
        rounding_account = RoundingUserAccount.objects.for_customer(
            user, fee_account.asset
        )
    return TapOperationAccounts(
        card_account=plastic_card_account.account,
        user_account=user_account,
        fee_account=fee_account,
        rounding_account=rounding_account
    )


def get_or_create_tap_customer_id(user) -> str:
    if not user.profile.tap_customer_id:
        currency = Asset.objects.main_fiat_for_customer(user)
        profile_qs = Profile.objects.select_for_update()
        with transaction.atomic(), get_tap_client() as tap_client:
            profile = profile_qs.get(user=user,
                                     tap_customer_id__isnull=True)
            kyc = profile.last_basic_kyc
            tap_customer = tap_client.create_customer(
                first_name=kyc.first_name,
                last_name=kyc.last_name,
                email=user.email,
                phone=Phone(country_code=profile.phone.code,
                            number=profile.phone.number),
                currency=currency.symbol
            )
            profile.tap_customer_id = tap_customer.id
            profile.save(update_fields=('tap_customer_id',))
    return profile.tap_customer_id


def create_charge_operation(user, asset, card_id, amount, hold=True):
    fee_amount = calculate_fee_card_deposit(
        amount=amount, asset=asset
    )
    accounts = get_tap_deposit_operation_accounts(user, asset, card_id)
    return Operation.objects.create_deposit(
        payment_method_account=accounts.card_account,
        user_account=accounts.user_account,

        fee_account=accounts.fee_account,
        fee_amount=fee_amount.rounded,

        rounding_account=accounts.rounding_account,
        rounding_amount=fee_amount.remainder,

        amount=amount,
        hold=hold,
    )


def fill_tap_charge_operation(operation, user, asset, amount, card_id):
    fee_amount = calculate_fee_card_deposit(amount=amount, asset=asset)
    accounts = get_tap_deposit_operation_accounts(user, asset, card_id)

    with transaction.atomic():
        # acquire lock
        op = Operation.objects.select_for_update().get(pk=operation.uuid)

        op.transactions.all().delete()

        op.transactions.create(account=accounts.card_account, amount=-amount)
        op.transactions.create(account=accounts.user_account, amount=amount)

        op.transactions.create(account=accounts.user_account, amount=-fee_amount.rounded)
        op.transactions.create(account=accounts.fee_account, amount=fee_amount.rounded)

        if fee_amount.remainder:
            op.transactions.create(account=accounts.card_account, amount=fee_amount.remainder)
            op.transactions.create(account=accounts.rounding_account, amount=-fee_amount.remainder)


def process_tap_charge(user, charge: Charge, card: Card):
    if charge.customer.id != user.profile.tap_customer_id:
        logger.error("Charge customer id %s didn't match user %s "
                     "tap customer id %s",
                     charge.customer.id,
                     user,
                     user.profile.tap_customer_id)
        raise CoinMENAException('charge_id', 'Invalid charge')

    asset = Asset.objects.main_fiat_for_customer(user)

    if charge.currency != asset.symbol:
        logger.error("Charge currency %s doesn't match user asset %s",
                     charge.currency, asset.symbol)
        raise CoinMENAException('charge_id', 'Invalid currency')

    charge_link, created = TapCharge.objects.get_or_create(charge_id=charge.id)

    amount = Decimal(str(charge.amount))

    if created:
        charge_link.operation = create_charge_operation(user, asset, card.id, amount)
        charge_link.save(update_fields=('operation',))
    elif charge_link.operation.status == Operation.NEW:
        # in case we received charge info about operation user created before
        with transaction.atomic():
            fill_tap_charge_operation(charge_link.operation, user, asset, amount, card.id)
            charge_link.operation.hold()

    if charge.status == ChargeStatus.CAPTURED:
        if charge_link.operation.status == Operation.HOLD:
            charge_link.operation.commit()
            logger.info(
                "Card deposit (operation=%s) success. Charge %s captured",
                charge_link.operation.uuid,
                charge.id
            )
        else:
            logger.info("Skip operation %s. Already processed.",
                        charge_link.operation.uuid)
    elif charge.status != ChargeStatus.INITIATED:
        logger.info("Card deposit (operation=%s) failed with status %s "
                    "(charge id %s)",
                    charge_link.operation.uuid,
                    charge.status,
                    charge.id)
        # TODO: more granular reason?
        charge_link.operation.reject('Card operation rejected')

    return charge_link.operation
