from django.apps import AppConfig


class AuthConfig(AppConfig):
    name = 'jibrel.authentication'

    def ready(self):
        """
        Signals connection

        :return:
        """
        import jibrel.authentication.signals.handler  # NOQA
