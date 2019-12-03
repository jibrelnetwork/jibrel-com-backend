import os

from celery import Celery

from jibrel.celery import SHARED_ROUTER_CONFIG

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jibrel_admin.settings')

app = Celery('jibrel_admin')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_routes = SHARED_ROUTER_CONFIG


def force_onfido_routine(basic_kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.enqueue_onfido_routine',
        kwargs={'basic_kyc_submission_id': basic_kyc_submission.id}
    )


def send_kyc_approved_mail(basic_kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.send_kyc_approved_mail',
        kwargs={'basic_kyc_submission_id': basic_kyc_submission.id}
    )


def send_kyc_rejected_mail(basic_kyc_submission):
    app.send_task(
        'jibrel.kyc.tasks.send_kyc_rejected_mail',
        kwargs={'basic_kyc_submission_id': basic_kyc_submission.id}
    )


# def send_fiat_withdrawal_approved_mail(user_id):
#     app.send_task(
#         'jibrel.payments.tasks.send_fiat_withdrawal_approved_mail',
#         kwargs={'user_id': str(user_id)}
#     )


# def send_fiat_withdrawal_rejected_mail(user_id, operation_id):
#     app.send_task(
#         'jibrel.payments.tasks.send_fiat_withdrawal_rejected_mail',
#         kwargs={'user_id': str(user_id), 'operation_id': str(operation_id)}
#     )


# def send_fiat_deposit_approved_mail(user_id):
#     app.send_task(
#         'jibrel.payments.tasks.send_fiat_deposit_approved_mail',
#         kwargs={'user_id': str(user_id)}
#     )


# def send_fiat_deposit_rejected_mail(user_id):
#     app.send_task(
#         'jibrel.payments.tasks.send_fiat_deposit_rejected_mail',
#         kwargs={'user_id': str(user_id)}
#     )


def send_password_reset_mail(user_ip: str, user_pk: str):
    app.send_task(
        'jibrel.authentication.tasks.send_password_reset_mail',
        kwargs={
            'user_ip': user_ip,
            'user_pk': user_pk
        }
    )
