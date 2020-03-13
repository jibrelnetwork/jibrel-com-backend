from django.core.management import BaseCommand

from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('transaction_id', nargs=1, type=str)

    @staticmethod
    def print_payment(payment):
        """
        {
            'id': 25932,
            'transaction_no': 'FLSAPI191145e6a2cd232505',
            'sender_id': 19114,
            'receiver_id': 17308,
            'payment_link_id': 0,
            'send_amount': 367.3,
            'sender_currency': 'AED',
            'tip_amount': 0,
            'receive_currency': 'AED',
            'special_offer_applied': 'No',
            'sender_amount': 367.3,
            'receive_amount': 367.3,
            'offer_amount': 0,
            'vat_amount': 0.91,
            'transaction_type': 'c-m',
            'poppay_fee': 18.18,
            'transaction_fixed_fee': 0,
            'customer_foloosi_fee': 0,
            'status': 'success',
            'created': '2020-03-12T12:36:34+00:00',
            'api_transaction': {
                'id': 42670,
                'sender_currency': 'USD',
                'payable_amount_in_sender_currency': 100
            },
            'receiver': {
                'id': 17308,
                'name': 'Faizan Jawed',
                'email': 'talal@jibrel.io',
                'business_name': 'Jibrel Limited'
            },
            'sender': {
                'id': 19114,
                'name': 'Talal',
                'email': 'test@jibrel.network',
                'business_name': None,
                'phone_number': '234234234234'
            }
        }
        """
        print(payment)
        # print(payment['transaction_no'])
        # print(payment['api_transaction']['payable_amount_in_sender_currency'],
        #       payment['api_transaction']['sender_currency'])
        # print(payment['status'])
        # print(payment.get('reference'))

    @staticmethod
    def get_payment(api, transaction_id):
        payment = api.get(transaction_id)
        Command.print_payment(payment)

    def handle(self, *args, **options):
        transaction_id = options['transaction_id'][0]
        api = FoloosiAPI()
        self.get_payment(api, transaction_id)
