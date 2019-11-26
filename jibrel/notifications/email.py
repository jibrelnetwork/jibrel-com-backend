import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional

from anymail.backends.mailgun import EmailBackend as AnymailMailgunBackend
from anymail.message import AnymailMessage
from django.conf import settings
from django.template import Template
from django.template.loader import select_template
from requests import Response


class EmailMessage(AnymailMessage):
    """Overridden email message with injected `postprocess_func` which would be called in EmailBackend"""

    postprocess_func: Optional[Callable[[Response], None]]

    def __init__(self, *args, **kwargs):
        self.postprocess_func = kwargs.pop('postprocess', None)
        super(EmailMessage, self).__init__(*args, **kwargs)


class EmailBackend(AnymailMailgunBackend):
    """Overridden EmailBackend which calls `postprocess_func` after getting response from ESP"""

    def post_to_esp(self, payload, message: EmailMessage) -> Response:
        response = super().post_to_esp(payload, message)
        if message.postprocess_func is not None:
            message.postprocess_func(response)
        return response


class TranslatableEmailMessage:
    META_PATH = os.path.join(settings.EMAIL_TEMPLATES_DIR, 'meta.json')
    _cached_meta = None

    def __init__(
        self,
        html_base_name: str,
        txt_base_name: str = None,
        fallback_language: str = 'en',
        from_email: str = settings.DEFAULT_FROM_EMAIL,
    ):
        self.html_base_name = html_base_name
        if txt_base_name is None:
            txt_base_name = html_base_name
        self.txt_base_name = txt_base_name
        self.fallback_language = fallback_language
        self.from_email = from_email
        self._cached_templates: Dict[str, EmailTemplate] = {}

    def translate(self, language: str) -> 'EmailTemplate':
        language = language.lower()
        if language not in self._cached_templates:
            html_template = select_template([
                self.get_html_template_name_for_language(l) for l in (language, self.fallback_language)
            ])
            txt_template = select_template([
                self.get_txt_template_name_for_language(l) for l in (language, self.fallback_language)
            ])
            html_template_name = html_template.origin.template_name.rsplit('/', maxsplit=1)[-1]
            self._cached_templates[language] = EmailTemplate(
                subject=self.get_subject(html_template_name),
                html_template=html_template,
                txt_template=txt_template,
                from_email=self.from_email,
            )
        return self._cached_templates[language]

    def get_html_template_name_for_language(self, language: str) -> str:
        return f'{self.html_base_name}-{language}.html'

    def get_txt_template_name_for_language(self, language: str) -> str:
        return f'{self.html_base_name}-{language}.html'  # todo add txt

    @classmethod
    def get_meta(cls):
        if cls._cached_meta is None:
            with open(cls.META_PATH, 'r') as f:
                cls._cached_meta = json.load(f)
        return cls._cached_meta

    @classmethod
    def get_subject(cls, filename: str) -> str:
        meta = cls.get_meta()
        return meta[filename]


class EmailTemplate:
    def __init__(
        self,
        subject: str,
        html_template: Template,
        txt_template: Template,
        from_email: str = settings.DEFAULT_FROM_EMAIL,
    ) -> None:
        self.subject = subject
        self.html_template = html_template
        self.txt_template = txt_template
        self.from_email = from_email

    def render(
        self,
        context: Dict[str, Any],
    ) -> 'RenderedEmailMessage':
        html_content = self.html_template.render(context)
        txt_content = self.txt_template.render(context)
        return RenderedEmailMessage(
            subject=self.subject,
            html_content=html_content,
            txt_content=txt_content,
            from_email=self.from_email
        )


@dataclass
class RenderedEmailMessage:
    subject: str
    html_content: str
    txt_content: str
    from_email: str

    def serialize(self):
        return asdict(self)


ConfirmationEmailMessage = TranslatableEmailMessage(
    html_base_name='email-confirm',
)

ResetPasswordEmailMessage = TranslatableEmailMessage(
    html_base_name='password-reset',
)

PhoneVerifiedEmailMessage = TranslatableEmailMessage(
    html_base_name='phone-verified',
)

KYCSubmittedEmailMessage = TranslatableEmailMessage(
    html_base_name='submission-verification-request',
)

KYCApprovedEmailMessage = TranslatableEmailMessage(
    html_base_name='submission-verification-approve',
)

KYCRejectedEmailMessage = TranslatableEmailMessage(
    html_base_name='submission-verification-reject',
)

LocalFiatWithdrawalRequestedEmailMessage = TranslatableEmailMessage(
    html_base_name='withdrawal-local-initiated',
)

FiatWithdrawalApprovedEmailMessage = TranslatableEmailMessage(
    html_base_name='withdrawal-approved',
)

FiatWithdrawalRejectedEmailMessage = TranslatableEmailMessage(
    html_base_name='withdrawal-canceled',
)

CryptoWithdrawalConfirmationEmailMessage = TranslatableEmailMessage(
    html_base_name='withdrawal-confirmation',
)

FiatDepositRequestedEmailMessage = TranslatableEmailMessage(
    html_base_name='deposit-initiated',
)

FiatDepositApprovedEmailMessage = TranslatableEmailMessage(
    html_base_name='deposit-approved',
)

FiatDepositRejectedEmailMessage = TranslatableEmailMessage(
    html_base_name='deposit-canceled',
)

BuyOrderExecutedEmailMessage = TranslatableEmailMessage(
    html_base_name='buy-order-executed'
)

SellOrderExecutedEmailMessage = TranslatableEmailMessage(
    html_base_name='sell-order-executed'
)
