from typing import List, Any

from rest_framework.request import Request
from zxcvbn import zxcvbn


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def is_strong_password(password: str, inputs: List[Any], required_score) -> bool:
    results = zxcvbn(password, user_inputs=inputs)
    return results['score'] >= required_score
