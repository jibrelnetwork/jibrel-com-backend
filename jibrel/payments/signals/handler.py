from django.db.models.signals import post_delete
from django.dispatch import receiver

from django_banking.contrib.wire_transfer.models import DepositWireTransferOperation
from django_banking.contrib.wire_transfer.signals import wire_transfer_deposit_approved, wire_transfer_deposit_rejected
from django_banking.models import Operation
from django_banking.user import User
from jibrel.notifications.email import (
    FiatDepositApprovedEmailMessage,
    FiatDepositRejectedEmailMessage,
    FiatDepositRequestedEmailMessage
)
from jibrel.notifications.tasks import send_mail


@receiver(wire_transfer_deposit_approved, sender=DepositWireTransferOperation)
def send_fiat_deposit_requested_mail(sender, instance, user_ip_address, *args, **kwargs):
    rendered = FiatDepositRequestedEmailMessage.translate(instance.user.profile.language).render({
        'name': instance.user.profile.username,
        'amount': f'{instance.amount} {instance.user_account.asset.symbol}',
    })
    send_mail.delay(
        recipient=instance.user.email,
        task_context={'user_id': instance.user.uuid.hex, 'user_ip_address': user_ip_address},
        **rendered.serialize(),
    )


@receiver(wire_transfer_deposit_approved, sender=DepositWireTransferOperation)
def send_fiat_deposit_approved_mail(sender, instance, *args, **kwargs):
    rendered = FiatDepositApprovedEmailMessage.translate(instance.user.profile.language).render({
        'name': instance.user.profile.username
    })
    send_mail.delay(
        recipient=instance.user.email,
        task_context={},
        **rendered.serialize()
    )


@receiver(wire_transfer_deposit_rejected, sender=DepositWireTransferOperation)
def send_fiat_deposit_rejected_mail(sender, instance, *args, **kwargs):
    rendered = FiatDepositRejectedEmailMessage.translate(instance.user.profile.language).render({
        'name': instance.user.profile.username,
    })
    send_mail.delay(
        recipient=instance.user.email,
        task_context={},
        **rendered.serialize()
    )


@receiver(wire_transfer_deposit_rejected, sender=DepositWireTransferOperation)
def send_crypto_deposit_requested_mail(sender, instance, *args, **kwargs):
    token = deposit_confirmation_token_generator.generate(request.user)
