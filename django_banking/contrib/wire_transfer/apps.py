from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class WireTransferConfig(AppConfig):
    name = 'django_banking.contrib.wire_transfer'
    verbose_name = _('Wire Transfer')
