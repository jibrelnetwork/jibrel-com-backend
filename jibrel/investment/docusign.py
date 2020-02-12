from typing import (
    Any,
    Dict
)

from django.conf import settings
from docusign_esign import (
    ApiClient,
    CompositeTemplate,
    EnvelopeDefinition,
    EnvelopesApi,
    InlineTemplate,
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
        composite_templates=[comp_template]
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
    def __init__(self, api_host=settings.DOCU_SIGN_API_HOST):
        api_client = ApiClient()
        api_client.host = api_host
        envelope_api = EnvelopesApi(api_client)
        self._api_client = api_client
        self._envelope_api = envelope_api
        self.authenticate()

    def authenticate(self):
        # todo
        import os
        access_key = os.getenv('DOCUSIGN_ACCESS_KEY')
        self._api_client.set_default_header('Authorization', f'Bearer {access_key}')

    def create_envelope(
        self,
        signer_email,
        signer_name,
        signer_user_id,
        template_id,
        account_id=settings.DOCU_SIGN_ACCOUNT_ID,
    ):
        envelope = get_envelope_definition(
            signer_email=signer_email,
            signer_name=signer_name,
            signer_user_id=signer_user_id,
            template_id=template_id,
            # todo
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
        account_id=settings.DOCU_SIGN_ACCOUNT_ID,
    ):
        recipient_view_request = get_recipient_view_request(
            signer_email=signer_email,
            signer_name=signer_name,
            signer_user_id=signer_user_id,
            return_url=return_url,
        )

        view = self._create_recipient_view(account_id, envelope_id, recipient_view_request)
        return view.url

    def get_envelope(self, envelope_id):
        return self._get_envelope(envelope_id)

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

    def _get_envelope(self, envelope_id, account_id=settings.DOCU_SIGN_ACCOUNT_ID):
        return self._envelope_api.get_envelope(
            account_id=account_id,
            envelope_id=envelope_id
        )
