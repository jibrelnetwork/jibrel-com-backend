from decimal import Decimal

from checkout_sdk.errors import CheckoutSdkError

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI

from .checkout_check import Command as CheckCommand


class Command(CheckCommand):
    def add_arguments(self, parser):
        parser.add_argument('token', nargs=1, type=str)
        parser.add_argument('amount', nargs=1, type=str)

    @staticmethod
    def request_payment(api, token, amount):
        try:
            payment = api.request_from_token(
                customer={
                    'email': 'test@jibrel.network',
                    'name': 'Talal'
                },
                token=token,
                amount=amount
            )
            CheckCommand.print_payment(payment)
        except CheckoutSdkError as e:
            print(e.error_type)

    def handle(self, *args, **options):
        amount = Decimal(options['amount'][0])
        token = options['token'][0]
        api = CheckoutAPI()
        self.request_payment(api, token, amount)
