import os
from datetime import timedelta

from celery import Celery
from django.urls import reverse
from django.utils import timezone

from jibrel.celery import SHARED_ROUTER_CONFIG
from jibrel.kyc.models import (
    BaseKYCSubmission,
    IndividualKYCSubmission,
    OrganisationalKYCSubmission
)
from jibrel_admin import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jibrel_admin.settings')

app = Celery('jibrel_admin')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_routes = SHARED_ROUTER_CONFIG


def force_onfido_routine(basic_kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.enqueue_onfido_routine',
        kwargs={'basic_kyc_submission_id': basic_kyc_submission.id}
    )


def send_kyc_approved_mail(kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.send_kyc_approved_mail',
        kwargs={
            'kyc_submission_id': kyc_submission.id,
            'account_type': kyc_submission.account_type
        }
    )


def send_kyc_rejected_mail(kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.send_kyc_rejected_mail',
        kwargs={
            'kyc_submission_id': kyc_submission.id,
            'account_type': kyc_submission.account_type
        }
    )


def send_password_reset_mail(user_ip: str, user_pk: str):
    app.send_task(
        'jibrel.authentication.tasks.send_password_reset_mail',
        kwargs={
            'user_ip': user_ip,
            'user_pk': user_pk
        }
    )


# @app.task()
def send_admin_new_kyc_notification():
    kyc = BaseKYCSubmission.objects.filter(
        created_at__gte=timezone.now() - timedelta(settings.KYC_ADMIN_NOTIFICATION_PERIOD),
        status=BaseKYCSubmission.PENDING
    )
    kyc_types = kyc.values_list('account_type', flat=True)
    admin_url = reverse('admin:kyc_{}_changelist'.format({
             BaseKYCSubmission.INDIVIDUAL: IndividualKYCSubmission.__name__.lower(),
             BaseKYCSubmission.BUSINESS: OrganisationalKYCSubmission.__name__.lower(),
         }[kyc_types[0]])) if len(set(kyc_types)) == 1 else reverse(
        'admin:app_list', args=("kyc",))
    kyc_count = len(kyc_types)

    # TODO: domain & schema
    app.send_task(
        'jibrel.kyc.tasks.send_admin_new_kyc_notification',
        kwargs={
            'admin_url': admin_url,
            'kyc_count': kyc_count
        }
    )
