from decimal import Decimal

from checkout_sdk.errors import CheckoutSdkError
from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('token', nargs=1, type=str)
        parser.add_argument('amount', nargs=1, type=str)

    def handle(self, *args, **options):
        token = options['token'][0]
        amount = Decimal(options['amount'][0])
        api = CheckoutAPI()
        try:
            payment = api.request_from_token(
                customer={
                    'email': 'test@jibrel.network',
                    'name': 'Talal'
                },
                token=token,
                amount=amount
            )
            print('----------------------------------')
            print(f'response_code: {payment.response_code}')
            print(f'response_summary: {payment.response_summary}')
            print('----------------------------------')
            print(f'user id: {payment.customer.id}')
            print(f'payment id: {payment.id}')
            print(f'status: {payment.status}')
            if payment.is_pending and payment.requires_redirect:
                print('redirect required')
                print(payment.redirect_link.href)
            print('----------------------------------')

        except CheckoutSdkError as e:
            print(e.error_type)
