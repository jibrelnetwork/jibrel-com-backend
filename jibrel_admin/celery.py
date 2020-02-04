import os

from celery import Celery

from jibrel.celery import SHARED_ROUTER_CONFIG

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jibrel_admin.settings')

app = Celery('jibrel_admin')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_routes = SHARED_ROUTER_CONFIG


def force_onfido_routine(kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.enqueue_onfido_routine_task',
        kwargs={
            'account_type': kyc_submission.account_type,
            'submission_id': kyc_submission.pk,
        }
    )
