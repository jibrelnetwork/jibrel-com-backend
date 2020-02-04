from typing import (
    Any,
    List
)

import phonenumbers
from zxcvbn import zxcvbn


def is_strong_password(password: str, inputs: List[Any], required_score) -> bool:
    results = zxcvbn(password, user_inputs=inputs)
    return results['score'] >= required_score


def is_valid_phone_number(number: str) -> bool:
    try:
        phone = phonenumbers.parse(number)
    except phonenumbers.NumberParseException:
        return False

    return phonenumbers.is_valid_number(phone)
