from django.apps import AppConfig


class InvestmentConfig(AppConfig):
    name = 'jibrel.investment'

    def ready(self):
        """
        Signals connection

        :return:
        """
        import jibrel.investment.signals.handler  # NOQA
