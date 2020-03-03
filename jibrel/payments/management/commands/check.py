from decimal import Decimal

from checkout_sdk.errors import CheckoutSdkError
from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('transaction_id', nargs=1, type=str)

    def handle(self, *args, **options):
        transaction_id = options['transaction_id'][0]
        api = CheckoutAPI()

        try:
            payment = api.get(transaction_id)
            print('----------------------------------')
            print(f'user id: {payment.customer.id}')
            print(f'payment id: {payment.id}')
            print(f'is pending: {payment.is_pending}')
            print(f'status: {payment.status}')

            if payment.is_pending and payment.requires_redirect:
                print('redirect required')
                print(payment.redirect_link.href)
            print('----------------------------------')

        except CheckoutSdkError as e:
            print(e.error_type)
