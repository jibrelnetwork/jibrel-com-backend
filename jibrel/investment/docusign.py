from datetime import timedelta
from typing import (
    Any,
    Dict
)

from django.conf import settings
from django.utils import timezone
from docusign_esign import (
    ApiClient,
    CompositeTemplate,
    EnvelopeDefinition,
    EnvelopesApi,
    InlineTemplate,
    OAuth,
    Recipients,
    RecipientViewRequest,
    ServerTemplate,
    Signer,
    Tabs,
    Text
)


def get_envelope_definition(
    signer_email,
    signer_name,
    signer_user_id,
    template_id,
    custom_fields: Dict[str, Any] = None
):
    if custom_fields is None:
        custom_fields = {}
    tabs = Tabs(
        text_tabs=[
            Text(
                tab_label=f'\\*{field}',
                value=f'{value}'
            )
            for field, value in custom_fields.items()
        ]
    )

    recipients = Recipients(
        signers=[
            Signer(
                recipient_id=1,
                email=signer_email,
                name=signer_name,
                role_name='Investor',
                client_user_id=signer_user_id,
                tabs=tabs
            )
        ]
    )

    comp_template = CompositeTemplate(
        server_templates=[
            ServerTemplate(sequence=1, template_id=template_id)
        ],
        inline_templates=[
            InlineTemplate(sequence=1, recipients=recipients)
        ]
    )

    return EnvelopeDefinition(
        status="sent",
        composite_templates=[comp_template],
        enable_wet_sign=False,
    )


def get_recipient_view_request(
    signer_email,
    signer_name,
    signer_user_id,
    return_url,
):
    return RecipientViewRequest(
        authentication_method='None',
        client_user_id=signer_user_id,
        return_url=return_url,
        user_name=signer_name,
        email=signer_email
    )


class DocuSignAPIException(Exception):
    pass


class DocuSignAPI:
    EXPIRES_IN = 8 * 3600
    _last_request = None
    _header_value = None

    def __init__(self, api_host=settings.DOCUSIGN_API_HOST, oauth_host_name=settings.DOCUSIGN_OAUTH_HOST):
        self._api_client = ApiClient(host=api_host, oauth_host_name=oauth_host_name)
        self._envelope_api = EnvelopesApi(self._api_client)
        self.authenticate()

    def authenticate(self):
        if settings.DOCUSIGN_TESTING:
            return
        if DocuSignAPI._last_request is not None:
            if self._last_request >= (timezone.now() + timedelta(seconds=int(self.EXPIRES_IN * 3/4))):
                self._api_client.set_default_header('Authorization', DocuSignAPI._header_value)
                return

        with open(settings.DOCUSIGN_PRIVATE_KEY_PATH, 'rb') as f:
            private_key = f.read()
        jwt = self._api_client.request_jwt_user_token(
            client_id=settings.DOCUSIGN_CLIENT_ID,
            user_id=settings.DOCUSIGN_USER_ID,
            oauth_host_name=self._api_client.oauth_host_name,
            private_key_bytes=private_key,
            expires_in=self.EXPIRES_IN,
            scopes=(OAuth.SCOPE_SIGNATURE, OAuth.SCOPE_IMPERSONATION),
        )
        DocuSignAPI._header_value = f'{jwt.token_type} {jwt.access_token}'
        DocuSignAPI._last_request = timezone.now()

    def create_envelope(
        self,
        signer_email,
        signer_name,
        signer_user_id,
        template_id,
        account_id=settings.DOCUSIGN_ACCOUNT_ID,
        custom_fields=None,
    ):
        envelope = get_envelope_definition(
            signer_email=signer_email,
            signer_name=signer_name,
            signer_user_id=signer_user_id,
            template_id=template_id,
            custom_fields=custom_fields,
        )
        envelope_summary = self._create_envelope(account_id, envelope)
        if envelope_summary.status != 'sent':
            raise DocuSignAPIException()
        return envelope_summary.envelope_id

    def create_recipient_view(
        self,
        envelope_id,
        signer_email,
        signer_name,
        signer_user_id,
        return_url,
        account_id=settings.DOCUSIGN_ACCOUNT_ID,
    ):
        recipient_view_request = get_recipient_view_request(
            signer_email=signer_email,
            signer_name=signer_name,
            signer_user_id=signer_user_id,
            return_url=return_url,
        )

        view = self._create_recipient_view(account_id, envelope_id, recipient_view_request)
        return view.url

    def get_envelope_status(self, envelope_id):
        envelope = self._get_envelope(envelope_id)
        return envelope.status

    def _create_envelope(self, account_id, envelope_definition: EnvelopeDefinition):
        return self._envelope_api.create_envelope(
            account_id,
            envelope_definition=envelope_definition,
        )

    def _create_recipient_view(self, account_id, envelope_id, recipient_view_request: RecipientViewRequest):
        return self._envelope_api.create_recipient_view(
            account_id,
            envelope_id,
            recipient_view_request=recipient_view_request
        )

    def _get_envelope(self, envelope_id, account_id=settings.DOCUSIGN_ACCOUNT_ID):
        return self._envelope_api.get_envelope(
            account_id=account_id,
            envelope_id=envelope_id
        )
