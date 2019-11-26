import functools

from django.http import HttpResponseBadRequest


def get_bad_request_response(msg: str) -> HttpResponseBadRequest:
    return HttpResponseBadRequest(
        f'<h1>{msg}</h1>'.encode('utf-8')
    )


def get_link_tag(url: str, name: str) -> str:
    return f'<a href="{url}" target="_blank">{name}</a>'


def force_empty_value_display(empty_value):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if not isinstance(result, bool) and not result:
                return empty_value
            return result

        return wrapper

    return decorator


def force_bool_value_display(true, false):
    mapping = {
        True: true,
        False: false,
    }

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if isinstance(result, bool):
                return mapping[result]
            return result

        return wrapper

    return decorator


def lazy(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    @functools.wraps(fn)
    def _lazyprop(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazyprop
