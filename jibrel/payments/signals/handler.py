from django.dispatch import receiver

from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation
)
from django_banking.contrib.wire_transfer.signals import (
    wire_transfer_deposit_approved,
    wire_transfer_deposit_rejected,
    wire_transfer_deposit_requested
)
from jibrel.notifications.email import (
    FiatDepositApprovedEmailMessage,
    FiatDepositRejectedEmailMessage,
    FiatDepositRequestedEmailMessage
)
from jibrel.notifications.utils import email_message_send


# @receiver(wire_transfer_deposit_requested, sender=DepositWireTransferOperation)
# def send_fiat_deposit_requested_mail(sender, instance, user_ip_address, *args, **kwargs):
#     email_message_send(
#         FiatDepositRequestedEmailMessage,
#         instance.user.email,
#         instance.user.profile.language,
#         kwargs={
#             'name': instance.user.profile.username,
#             'amount': f'{instance.amount} {instance.user_account.asset.symbol}',
#             'user_id': instance.user.uuid.hex,
#             'user_ip_address': user_ip_address
#         }
#     )


@receiver(wire_transfer_deposit_approved, sender=DepositWireTransferOperation)
def send_fiat_deposit_approved_mail(sender, instance, *args, **kwargs):
    email_message_send(
        FiatDepositApprovedEmailMessage,
        instance.user.email,
        instance.user.profile.language,
        kwargs={
            'name': instance.user.profile.username
        }
    )


@receiver(wire_transfer_deposit_rejected, sender=DepositWireTransferOperation)
def send_fiat_deposit_rejected_mail(sender, instance, *args, **kwargs):
    email_message_send(
        FiatDepositRejectedEmailMessage,
        instance.user.email,
        instance.user.profile.language,
        kwargs={
            'name': instance.user.profile.username
        }
    )


@receiver(wire_transfer_deposit_rejected, sender=DepositWireTransferOperation)
def send_crypto_deposit_requested_mail(sender, instance, *args, **kwargs):
    # TODO
    # token = deposit_confirmation_token_generator.generate(request.user)
    pass
