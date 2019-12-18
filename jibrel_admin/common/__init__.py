from django.utils.safestring import mark_safe


@mark_safe
def display_boolean(func):
    yn = {
        True: '/static/admin/img/icon-yes.svg',
        False: '/static/admin/img/icon-no.svg',
    }

    def wrapper(*args, **kwargs):
        val = func(*args, **kwargs)
        return f'<img src="{yn[bool(val)]}"/>'

    return wrapper
