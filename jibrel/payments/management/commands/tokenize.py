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

    def handle(self, *args, **options):
        expiry_month, expiry_year = options['expiry'][0].split('/')
        api = CheckoutAPI()

        data = dict(
            number=''.join(options['number']),
            expiry_month=expiry_month,
            expiry_year=expiry_year,
        )
        if options.get('name'):
            data['name'] = options['name']
        if options.get('cvv'):
            data['cvv'] = options['cvv']

        response = api.tokenize(**data)
        data = response.body
        print(data)
        print('----------------------------------')
        print(f'token: {data["token"]}')
        print(f'expires on {data["expires_on"]}')
        print('----------------------------------')
