from decimal import Decimal

from checkout_sdk.errors import CheckoutSdkError
from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('number', nargs=4, type=str)
        parser.add_argument('expiry', nargs=1, type=str)
        parser.add_argument('amount', nargs=1, type=str)
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
        amount = Decimal(options['amount'][0])
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
        token = response.body["token"]

        try:
            payment = api.request_from_token(
                customer={
                    'email': 'test@jibrel.network',
                    'name': 'Talal'
                },
                token=token,
                amount=amount
            )
            # print('----------------------------------')
            # print(f'response_code: {payment.response_code}')
            # print(f'response_summary: {payment.response_summary}')
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
