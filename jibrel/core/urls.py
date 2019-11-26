from django.urls import path as real_path


def path(route, *args, **kwargs):
    route = route.rstrip('/')
    return [
        real_path(route, *args, **kwargs),
        real_path(f'{route}/', *args, **kwargs),
    ]
