import functools

from django.utils.safestring import mark_safe


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


empty_value_display = force_empty_value_display('-')


def get_link_tag(url: str, name: str) -> str:
    return f'<a href="{url}" target="_blank">{name}</a>'


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


display_boolean = mark_safe(force_bool_value_display(
    '/static/admin/img/icon-yes.svg',
    '/static/admin/img/icon-no.svg'
))
