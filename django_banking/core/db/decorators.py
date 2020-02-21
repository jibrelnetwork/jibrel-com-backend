import functools


def annotated(method):
    @functools.wraps(method)
    def wrapper(obj, *args, **kwargs):
        name = f'{method.__name__}_'
        if hasattr(obj, name):
            return getattr(obj, name)
        return method(obj, *args, **kwargs)
    return wrapper
