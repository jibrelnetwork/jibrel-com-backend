from typing import Any, List

import phonenumbers
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


def is_valid_phone_number(number: str) -> bool:
    try:
        phone = phonenumbers.parse(number)
    except phonenumbers.NumberParseException:
        return False

    return phonenumbers.is_valid_number(phone)
