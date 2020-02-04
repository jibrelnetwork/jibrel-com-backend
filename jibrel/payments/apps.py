from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = 'jibrel.payments'

    def ready(self):
        """
        Signals connection

        :return:
        """
        import jibrel.payments.signals.handler  # NOQA
