import webbrowser
from decimal import Decimal

from django.conf import settings

from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI

from .foloosi_check import Command as CheckCommand


class Command(CheckCommand):
    def add_arguments(self, parser):
        parser.add_argument('amount', nargs=1, type=str)
        parser.add_argument(
            '--redirect_url',
            action='store',
            type=str
        )

    @staticmethod
    def request_payment(api, redirect_url, amount):
        payment = api.request(
            customer={
                'email': 'test@jibrel.network',
                'name': 'Talal'
            },
            redirect_url=redirect_url,
            amount=amount
        )
        print("Card Number: 4111111111111111")
        print("Expiry: 05/20")
        print("CVV: 123\n")
        print("Card Number: 4242424242424242")
        print("Expiry: 05/23")
        print("CVV: 123\n")

        reference_token = payment['data']['reference_token']
        url = f'https://widget.foloosi.com/?{{"reference_token":"{reference_token}","secret_key":"{settings.FOLOOSI_MERCHANT_KEY}"}}'
        webbrowser.open(url)

    def handle(self, *args, **options):
        amount = Decimal(options['amount'][0])
        redirect_url = options.get('redirect_url', '')
        api = FoloosiAPI()
        self.request_payment(api, redirect_url, amount)
