from django.core.management import BaseCommand

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'webhook_id',
            action='store',
            type=str
        )
        parser.add_argument(
            'event_id',
            action='store',
            type=str
        )

    def handle(self, *args, **options):
        webhook_id = options['webhook_id']
        event_id = options['event_id']
        api = CheckoutAPI()
        api.retry_webhook(webhook_id, event_id)
        print('retried')
