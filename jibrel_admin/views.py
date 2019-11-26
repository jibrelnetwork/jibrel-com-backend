from django.conf import settings
from django.http import JsonResponse


def healthcheck(request):
    return JsonResponse({
        'healthy': True,
        'version': getattr(settings, 'VERSION', 'undefined')
    })
