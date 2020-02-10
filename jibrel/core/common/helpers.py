from django.http import HttpResponseBadRequest


def get_bad_request_response(msg: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(
        f'<h1>{msg}</h1>'.encode('utf-8')
    )


def get_from_qs(method):
    def wrapper(obj, *args, **kwargs):
        return getattr(obj, f'{method.__name__}_', None) or method(obj, *args, **kwargs)
    return wrapper
