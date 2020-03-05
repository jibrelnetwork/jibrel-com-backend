import os

from celery import Celery

SHARED_ROUTER_CONFIG = {

    # actual email sending task
    'jibrel.notifications.tasks.send_mail': {
        'queue': 'email'
    },

    # email generation tasks
    'jibrel.exchanges.tasks.send_order_completed_mail': {
        'queue': 'default'
    },
    'jibrel.kyc.tasks.send_admin_new_kyc_notification': {
        'queue': 'default'
    },

    'jibrel.payments.tasks.send_fiat_withdrawal_approved_mail': {
        'queue': 'default'
    },
    'jibrel.payments.tasks.send_fiat_withdrawal_rejected_mail': {
        'queue': 'default'
    },
    'jibrel.payments.tasks.send_fiat_deposit_approved_mail': {
        'queue': 'default'
    },
    'jibrel.payments.tasks.send_fiat_deposit_rejected_mail': {
        'queue': 'default'
    },

    # DocuSign
    'jibrel.investment.tasks.docu_sign_start_task': {
        'queue': 'default'
    },
    'jibrel.investment.tasks.docu_sign_finish_task': {
        'queue': 'default'
    },


    # SMS/twilio tasks
    'jibrel.kyc.tasks.send_verification_code': {
        'queue': 'twilio'
    },
    'jibrel.kyc.tasks.check_verification_code': {
        'queue': 'twilio'
    },

    # Onfido tasks
    'jibrel.kyc.tasks.enqueue_onfido_routine_task': {
        'queue': 'default'
    },
    'jibrel.kyc.tasks.onfido_create_applicant_task': {
        'queue': 'onfido'
    },
    'jibrel.kyc.tasks.onfido_upload_document_task': {
        'queue': 'onfido'
    },

    'jibrel.kyc.tasks.onfido_start_check_task': {
        'queue': 'onfido'
    },
    'jibrel.kyc.tasks.onfido_save_check_result_task': {
        'queue': 'onfido'
    },

    'jibrel.kyc.tasks.onfido_create_applicant_beneficiary_task': {
        'queue': 'onfido'
    },

    'jibrel.kyc.tasks.onfido_start_check_beneficiary_task': {
        'queue': 'onfido'
    },

    'jibrel.kyc.tasks.onfido_save_check_result_beneficiary_task': {
        'queue': 'onfido'
    },

    # Tap-related tasks
    'jibrel.payments.tasks.install_webhook': {
        'queue': 'payments'
    },
    'jibrel.payments.tasks.checkout_get': {
        'queue': 'payments'
    },
    'jibrel.payments.tasks.checkout_request': {
        'queue': 'payments'
    },
}

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jibrel.settings')

app = Celery('jibrel')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.task_routes = SHARED_ROUTER_CONFIG


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # sender.add_periodic_task(
    #     settings.EXCHANGE_PRICES_RECALCULATION_SCHEDULE,
    #     signature('jibrel.exchanges.tasks.calculate_and_update_prices_task'),
    # )
    # sender.add_periodic_task(
    #     settings.EXCHANGE_FETCH_TRANSACTIONS_SCHEDULE,
    #     signature('jibrel.exchanges.tasks.fetch_transactions'),
    # )
    # sender.add_periodic_task(
    #     settings.EXCHANGE_FETCH_TRADES_SCHEDULE,
    #     signature('jibrel.exchanges.tasks.fetch_trades'),
    # )
    # sender.add_periodic_task(
    #     settings.TAP_CHARGE_PROCESSING_SCHEDULE,
    #     signature('jibrel.payments.tasks.fetch_charges')
    # )
    # sender.add_periodic_task(
    #     settings.KRAKEN_UPDATE_BALANCE_SCHEDULE,
    #     signature('jibrel.payments.tasks.update_balances_task')
    # )
    # sender.add_periodic_task(
    #     settings.MARKET_BALANCE_CHECKING_SCHEDULE,
    #     signature('jibrel.exchanges.tasks.validate_unprocessed_orders_task'),
    # )
    pass
