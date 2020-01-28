from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DjangoBankingConfig(AppConfig):
    name = 'django_banking'
    verbose_name = _('Django Banking')
