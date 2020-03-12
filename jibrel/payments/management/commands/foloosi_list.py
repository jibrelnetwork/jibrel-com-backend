from django.core.management import BaseCommand

from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI

from .foloosi_check import Command as CheckComand


class Command(BaseCommand):
    @staticmethod
    def print_payments(data):
        print(f'Total Transactions: {data["total_count"]}')
        transactions = data['transactions']
        for transaction in transactions:
            CheckComand.print_payment(transaction)

    @staticmethod
    def get_payments(api):
        Command.print_payments(api.list()['data'])

    def handle(self, *args, **options):
        api = FoloosiAPI()
        self.get_payments(api)
