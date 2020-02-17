import functools

from django.http import HttpResponseBadRequest


def get_bad_request_response(msg: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(
        f'<h1>{msg}</h1>'.encode('utf-8')
    )


def get_from_qs(method):
    @functools.wraps(method)
    def wrapper(obj, *args, **kwargs):
        name = f'{method.__name__}_'
        if hasattr(obj, name):
            return getattr(obj, name)
        return method(obj, *args, **kwargs)
    return wrapper
