from django.dispatch import receiver

from django_banking.user import User
from jibrel.authentication.services import request_password_reset
from jibrel.authentication.signals import password_reset_requested


@receiver(password_reset_requested, sender=User)
def send_password_reset_email(sender, instance, user_ip_address, *args, **kwargs):
    request_password_reset(user_ip_address, instance.email)
