import os

from celery import Celery

SHARED_ROUTER_CONFIG = {
    # general price tasks
    'jibrel.exchanges.tasks.update_prices_task': {
        'queue': 'prices'
    },
    'jibrel.exchanges.tasks.calculate_and_update_prices_task': {
        'queue': 'prices'
    },

    # prices per provider
    'jibrel.exchanges.tasks.update_fiat_prices_task': {
        'queue': 'prices'
    },
    'jibrel.exchanges.tasks.update_crypto_prices_task': {
        'queue': 'prices'
    },

    # orders and processing tasks
    'jibrel.exchanges.tasks.add_order': {
        'queue': 'orders'
    },
    'jibrel.exchanges.tasks.fetch_transactions': {
        'queue': 'orders'
    },
    'jibrel.exchanges.tasks.fetch_trades': {
        'queue': 'orders'
    },
    'jibrel.exchanges.tasks.commit_exchange_operations': {
        'queue': 'default'  # only updates db
    },
    'jibrel.exchanges.tasks.update_balances_task': {
        'queue': 'orders'
    },
    'jibrel.exchanges.tasks.validate_unprocessed_orders_task': {
        'queue': 'orders'
    },

    # actual email sending task
    'jibrel.notifications.tasks.send_mail': {
        'queue': 'email'
    },

    # email generation tasks
    'jibrel.exchanges.tasks.send_order_completed_mail': {
        'queue': 'default'
    },
    'jibrel.authentication.tasks.send_password_reset_mail': {
        'queue': 'default'
    },
    'jibrel.kyc.tasks.send_kyc_submitted_mail': {
        'queue': 'default'
    },
    'jibrel.kyc.tasks.send_kyc_approved_mail': {
        'queue': 'default'
    },
    'jibrel.kyc.tasks.send_kyc_rejected_mail': {
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

    # SMS/twilio tasks
    'jibrel.kyc.tasks.send_verification_code': {
        'queue': 'twilio'
    },
    'jibrel.kyc.tasks.check_verification_code': {
        'queue': 'twilio'
    },

    # Onfido tasks
    'jibrel.kyc.tasks.enqueue_onfido_routine': {
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

    # Tap-related tasks
    'jibrel.payments.tasks.process_charge': {
        'queue': 'tap_payments'
    },
    'jibrel.payments.tasks.fetch_charges': {
        'queue': 'tap_payments'
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
