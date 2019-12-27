from django.dispatch import receiver

from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)
from jibrel.kyc.signals import (
    kyc_approved,
    kyc_requested,
    kyc_rejected)
from jibrel.notifications.email import (
    KYCApprovedEmailMessage,
    KYCRejectedEmailMessage,
    KYCSubmittedEmailMessage
)
from jibrel.notifications.utils import email_message_send


@receiver(kyc_approved, sender=IndividualKYCSubmission)
@receiver(kyc_approved, sender=OrganisationalKYCSubmission)
def send_kyc_approved_mail(sender, instance, *args, **kwargs):
    user = instance.profile.user
    email_message_send(
        KYCApprovedEmailMessage,
        user.email,
        user.profile.language,
        kwargs={
            'name': user.profile.username,
            'email': user.email,
        }
    )


@receiver(kyc_rejected, sender=IndividualKYCSubmission)
@receiver(kyc_rejected, sender=OrganisationalKYCSubmission)
def send_kyc_rejected_mail(sender, instance, *args, **kwargs):
    user = instance.profile.user
    email_message_send(
        KYCRejectedEmailMessage,
        user.email,
        user.profile.language,
        kwargs={
            'name': user.profile.username,
            'email': user.email,
            'reject_reason': instance.reject_reason,
        }
    )


@receiver(kyc_requested, sender=IndividualKYCSubmission)
@receiver(kyc_requested, sender=OrganisationalKYCSubmission)
def send_kyc_submitted_mail(sender, instance, *args, **kwargs):
    user = instance.profile.user
    email_message_send(
        KYCSubmittedEmailMessage,
        user.email,
        user.profile.language,
        kwargs={
            'name': user.profile.username,
            'email': user.email,
        }
    )
