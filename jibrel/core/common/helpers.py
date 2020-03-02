import functools

from django.http import HttpResponseBadRequest


def get_bad_request_response(msg: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(
        f'<h1>{msg}</h1>'.encode('utf-8')
    )


def default_value_for_new_object(value):
    def decorator(method):
        @functools.wraps(method)
        def wrapper(obj, *args, **kwargs):
            if getattr(obj._state, 'adding', True):
                return value
            return method(obj, *args, **kwargs)
        return wrapper
    return decorator
