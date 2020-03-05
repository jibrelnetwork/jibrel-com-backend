from checkout_sdk.errors import CheckoutSdkError
from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('transaction_id', nargs=1, type=str)

    @staticmethod
    def print_payment(payment):
        print(
            '----------------------------------\n' +
            f'User id: {payment.customer.id}\n' +
            f'Payment id: {payment.id}\n' +
            f'Is pending: {payment.is_pending}\n' +
            f'Status: {payment.status}\n' +
            f'Redirect required: {payment.redirect_link.href}\n' +
            '----------------------------------\n'
        )

        if payment.is_pending and payment.requires_redirect:
            print(
                f'Redirect required: {payment.redirect_link.href}\n' +
                '----------------------------------\n'
            )

    @staticmethod
    def get_payment(api, transaction_id):
        try:
            payment = api.get(transaction_id)
            Command.print_payment(payment)
        except CheckoutSdkError as e:
            print(e.error_type)

    def handle(self, *args, **options):
        transaction_id = options['transaction_id'][0]
        api = CheckoutAPI()
        self.get_payment(api, transaction_id)
