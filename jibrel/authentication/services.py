from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction

from jibrel.authentication.models import (
    Profile,
    User
)
from jibrel.authentication.token_generator import (
    activate_reset_password_token_generator,
    complete_reset_password_token_generator,
    verify_token_generator
)
from jibrel.core.errors import (
    ConflictException,
    InvalidException,
    WrongPasswordException
)
from jibrel.core.limits import (
    ResendVerificationEmailLimiter,
    ResetPasswordLimiter
)
from jibrel.notifications.email import (
    ConfirmationEmailMessage,
    ResetPasswordEmailMessage
)
from jibrel.notifications.tasks import send_mail


@transaction.atomic()
def register(
    *,
    email: str,
    password: str,
    username: str,
    first_name: str,
    last_name: str,
    is_agreed_documents: bool,
    language: str,
) -> Profile:
    """Register user and create his profile

    :param email: Should be unique
    :param password:
    :param username:
    :param first_name:
    :param last_name:
    :param is_agreed_documents:
    :param language:
    """
    user = User.objects.create(
        email=email,
        is_email_confirmed=False,
        password=make_password(password),
    )
    profile = Profile.objects.create(
        user=user,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_agreed_documents=is_agreed_documents,
        language=language,
    )
    return profile


def change_password(user: User, old_password: str, new_password: str):
    if not user.check_password(old_password):
        raise WrongPasswordException.for_field('oldPassword')
    user.password = make_password(new_password)
    user.save()


def send_verification_email(user: User, user_ip: str):
    """Send email message with verification code to `user`s email address

    Args:
        user: User which email would be verified
        user_ip: User IP address stored to security purpose

    Returns:
        None
    """
    ResendVerificationEmailLimiter(user).is_throttled(raise_exception=True)
    token = verify_token_generator.generate(user)

    rendered = ConfirmationEmailMessage.render({
        'name': user.profile.username,
        'token': token.hex,
        'email': user.email
    }, language=user.profile.language)
    send_mail.delay(
        task_context={'user_id': user.uuid.hex, 'user_ip_address': user_ip},
        recipient=user.email,
        **rendered.serialize()
    )


def verify_user_email_by_key(key: UUID) -> User:
    """Toggle `is_email_confirmed` flag of `user` taken by `key` token if it is valid

    Args:
        key:

    Returns:
        User with confirmed email
    """

    ott = verify_token_generator.validate(key)
    if ott is None:
        raise InvalidException('key')
    elif not ott.user.is_active:
        raise ConflictException('user blocked')
    elif ott.user.is_email_confirmed:
        raise ConflictException('user activated already')
    ott.user.is_email_confirmed = True
    ott.user.save()
    return ott.user


def request_password_reset(user_ip: str, email: UUID):
    try:
        user = User.objects.select_related('profile').get(email=email)
    except User.DoesNotExist:
        return
    if ResetPasswordLimiter(user).is_throttled(raise_exception=False):
        return
    token = activate_reset_password_token_generator.generate(user)
    rendered = ResetPasswordEmailMessage.render({
        'name': user.profile.username,
        'expiration_hours': settings.FORGOT_PASSWORD_EMAIL_TOKEN_LIFETIME // 60 // 60,
        'token': token.hex,
        'email': user.email
    }, language=user.profile.language)
    send_mail.delay(
        task_context=dict(user_ip_address=user_ip),
        recipient=user.email,
        **rendered.serialize()
    )


def activate_password_reset(key: UUID):
    ott = activate_reset_password_token_generator.validate(key)
    if ott is None or ott.checked_already:
        raise InvalidException('key')
    complete_reset_password_token_generator.generate(ott.user, key)


@transaction.atomic()
def reset_password_complete(key: UUID, password: str):
    ott = complete_reset_password_token_generator.validate(key)
    if ott is None or ott.checked_already:
        raise InvalidException.for_field('key')
    ott.user.set_password(password)
    ott.user.save()
