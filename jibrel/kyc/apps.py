from django.apps import AppConfig


class KycConfig(AppConfig):
    name = 'jibrel.kyc'

    def ready(self):
        """
        Signals connection

        :return:
        """
        import jibrel.kyc.signals.handler  # NOQA
