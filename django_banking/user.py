from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from .settings import USER_MODEL

try:
    User = django_apps.get_model(USER_MODEL, require_ready=False)
except ValueError:
    raise ImproperlyConfigured("CCWT_USER_MODEL must be of the form 'app_label.model_name'")
except LookupError:
    raise ImproperlyConfigured(
        "CCWT_USER_MODEL refers to model '%s' that has not been installed" % settings.AUTH_USER_MODEL
    )
