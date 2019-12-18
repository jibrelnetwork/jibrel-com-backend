import uuid
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models.functions import Now

from jibrel.authentication.models import (
    OneTimeToken,
    User
)

VERIFY_EMAIL_TOKEN_LIFETIME = settings.VERIFY_EMAIL_TOKEN_LIFETIME

FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME = settings.FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME


class TokenGenerator:
    def __init__(self, lifetime: int, operation_type: int):
        self.lifetime = lifetime
        self.operation_type = operation_type

    def generate(
        self,
        user: User,
        token: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        if token is None:
            token = uuid.uuid4()
        token_obj = OneTimeToken.objects.create(
            user=user,
            token=token,
            operation_type=self.operation_type,
        )
        return token_obj.token

    @transaction.atomic()
    def validate(self, token: uuid.UUID) -> Optional[User]:
        try:
            token_obj = OneTimeToken.objects.get(
                token=token,
                checked=False,
                operation_type=self.operation_type,
                created_at__gte=Now() - timedelta(seconds=self.lifetime),
            )
        except OneTimeToken.DoesNotExist:
            return None
        token_obj.checked = True
        token_obj.save()
        return token_obj.user


verify_token_generator = TokenGenerator(
    lifetime=VERIFY_EMAIL_TOKEN_LIFETIME,
    operation_type=OneTimeToken.EMAIL_VERIFICATION,
)

activate_reset_password_token_generator = TokenGenerator(
    lifetime=FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME,
    operation_type=OneTimeToken.PASSWORD_RESET_ACTIVATE
)

complete_reset_password_token_generator = TokenGenerator(
    lifetime=FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME,
    operation_type=OneTimeToken.PASSWORD_RESET_COMPLETE
)

deposit_confirmation_token_generator = TokenGenerator(
    lifetime=3600,
    operation_type=OneTimeToken.CRYPTO_WITHDRAWAL_CONFIRMATION
)
