from django.conf import settings
from django.core.management import BaseCommand
from django.urls import reverse

from django_banking.contrib.card.backend.checkout.backend import CheckoutAPI


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            action='store',
            type=str
        )

    def handle(self, *args, **options):
        api = CheckoutAPI()
        host = options.get('host') or f'http://{settings.DOMAIN_NAME}'
        url = f'{host.rstrip("/")}{reverse("checkout-webhook")}'
        response = api.install_webhook(url)
        data = response.body
        print(
            f'webhook: {data["url"]}\n' +
            f'id: {data["id"]}\n'
        )
