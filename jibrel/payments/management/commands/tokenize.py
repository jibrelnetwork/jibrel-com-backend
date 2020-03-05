from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('number', nargs=4, type=str)
        parser.add_argument('expiry', nargs=1, type=str)
        parser.add_argument(
            '--name',
            action='store',
            type=str
        )
        parser.add_argument(
            '--cvv',
            action='store',
            type=str
        )

    @staticmethod
    def get_token(api, **options):
        expiry_month, expiry_year = options['expiry'][0].split('/')

        data = {
            'number': ''.join(options['number']),
            'expiry_month': expiry_month,
            'expiry_year': expiry_year
        }

        response = api.tokenize(**data)
        data = response.body
        print(
            f'token: {data["token"]}\n' +
            f'expires on {data["expires_on"]}\n'
        )
        return data["token"]

    def handle(self, *args, **options):
        api = CheckoutAPI()
        self.get_token(api, **options)
