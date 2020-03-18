import uuid
from ipware import get_client_ip

import structlog
import traceback
from django.http import Http404

logger = structlog.getLogger('request')


def get_request_header(request, header_key, meta_key):
    if hasattr(request, "headers"):
        return request.headers.get(header_key)

    return request.META.get(meta_key)


class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = get_request_header(
            request, "x-request-id", "HTTP_X_REQUEST_ID"
        ) or str(uuid.uuid4())

        with structlog.threadlocal.tmp_bind(logger):
            logger.bind(request_id=request_id)

            if hasattr(request, "user") and request.user.is_authenticated:
                logger.bind(user_id=str(request.user.pk))

            ip, _ = get_client_ip(request)
            logger.bind(ip=ip)

            return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Http404):
            # We don't log an exception here, and we don't set that we handled
            # an error as we want the standard `request_finished` log message
            # to be emitted.
            return

        traceback_object = exception.__traceback__
        formatted_traceback = traceback.format_tb(traceback_object)
        logger.exception(
            "request_failed",
            code=500,
            request=request,
            error=exception,
            error_traceback=formatted_traceback,
        )
