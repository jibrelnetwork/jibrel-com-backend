from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction

from jibrel.authentication.models import Profile, User
from jibrel.authentication.token_generator import (
    activate_reset_password_token_generator,
    complete_reset_password_token_generator,
    verify_token_generator
)
from jibrel.core.errors import InvalidException, WrongPasswordException
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
    is_agreed_terms: bool,
    is_agreed_privacy_policy: bool,
    language: str,
) -> Profile:
    """Register user and create his profile

    :param email: Should be unique
    :param password:
    :param username:
    :param is_agreed_terms:
    :param is_agreed_privacy_policy:
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
        is_agreed_terms=is_agreed_terms,
        is_agreed_privacy_policy=is_agreed_privacy_policy,
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

    user = verify_token_generator.validate(key)
    if user is None:
        raise InvalidException('key')
    elif not user.is_active:
        raise InvalidException('key', 'user blocked')
    elif user.is_email_confirmed:
        raise InvalidException('key', 'user activated already')
    user.is_email_confirmed = True
    user.save()
    return user


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
    user = activate_reset_password_token_generator.validate(key)
    if user is None:
        raise InvalidException('key')
    complete_reset_password_token_generator.generate(user, key)


@transaction.atomic()
def reset_password_complete(key: UUID, password: str):
    user = complete_reset_password_token_generator.validate(key)
    if user is None:
        raise InvalidException.for_field('key')
    user.set_password(password)
    user.save()
