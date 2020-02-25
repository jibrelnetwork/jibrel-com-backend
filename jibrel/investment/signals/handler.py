from django.dispatch import receiver

from jibrel.investment.models import (
    InvestmentApplication,
    InvestmentSubscription
)
from jibrel.investment.signals import (
    investment_submitted,
    waitlist_submitted
)
from jibrel.notifications.email import (
    InvestSubmittedEmailMessage,
    WaitlistSubmittedEmailMessage
)
from jibrel.notifications.utils import email_message_send


@receiver(investment_submitted, sender=InvestmentApplication)
def send_investment_submitted_mail(sender, instance, asset, *args, **kwargs):
    user = instance.user
    email_message_send(
        InvestSubmittedEmailMessage,
        recipient=user.email,
        language=user.profile.language,
        kwargs={
            'name': f'{user.profile.first_name} {user.profile.last_name}',
            'subscriptionAmount': f'{instance.amount:.2f} {asset.symbol}',
            'companyName': instance.offering.security.company.name,
            **kwargs,
        }
    )


@receiver(waitlist_submitted, sender=InvestmentSubscription)
def send_waitlist_submitted_mail(sender, instance, *args, **kwargs):
    user = instance.user
    email_message_send(
        WaitlistSubmittedEmailMessage,
        recipient=instance.email,
        language=user.profile.language,
        kwargs={
            'startupName': instance.offering.security.company.name
        }
    )
