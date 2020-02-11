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
    if custom_fields is not None:
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
        access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjY4MTg1ZmYxLTRlNTEtNGNlOS1hZjFjLTY4OTgxMjIwMzMxNyJ9.eyJUb2tlblR5cGUiOjUsIklzc3VlSW5zdGFudCI6MTU4MTA2ODc4MiwiZXhwIjoxNTgxMDk3NTgyLCJVc2VySWQiOiI2MDBjMWVhNi00MmFlLTRhYTYtYjY0YS1iMWU1ZTljOTNiZmMiLCJzaXRlaWQiOjEsInNjcCI6WyJzaWduYXR1cmUiLCJjbGljay5tYW5hZ2UiLCJvcmdhbml6YXRpb25fcmVhZCIsInJvb21fZm9ybXMiLCJncm91cF9yZWFkIiwicGVybWlzc2lvbl9yZWFkIiwidXNlcl9yZWFkIiwidXNlcl93cml0ZSIsImFjY291bnRfcmVhZCIsImRvbWFpbl9yZWFkIiwiaWRlbnRpdHlfcHJvdmlkZXJfcmVhZCIsImR0ci5yb29tcy5yZWFkIiwiZHRyLnJvb21zLndyaXRlIiwiZHRyLmRvY3VtZW50cy5yZWFkIiwiZHRyLmRvY3VtZW50cy53cml0ZSIsImR0ci5wcm9maWxlLnJlYWQiLCJkdHIucHJvZmlsZS53cml0ZSIsImR0ci5jb21wYW55LnJlYWQiLCJkdHIuY29tcGFueS53cml0ZSJdLCJhdWQiOiJmMGYyN2YwZS04NTdkLTRhNzEtYTRkYS0zMmNlY2FlM2E5NzgiLCJhenAiOiJmMGYyN2YwZS04NTdkLTRhNzEtYTRkYS0zMmNlY2FlM2E5NzgiLCJpc3MiOiJodHRwczovL2FjY291bnQtZC5kb2N1c2lnbi5jb20vIiwic3ViIjoiNjAwYzFlYTYtNDJhZS00YWE2LWI2NGEtYjFlNWU5YzkzYmZjIiwiYXV0aF90aW1lIjoxNTgxMDY3NDQ4LCJwd2lkIjoiMTVjYzlhNDItM2I5Ny00MGM1LWI0YWEtYmQxYWQ0YWMzNDMxIn0.Su_5RQSMgDys1RVj2c22v5LLHM9Zr4ERURjomnaWE6w0I9utVrQTPZgrqTAvGv30VFNqNk3D1nFbUIodFfIgJRKiL4DXiWDvIc-LP6MrGx_Op10g56yFLHJWogPxfHM15MNODftUzj-GHRqZbF7pQhmC47botgW2oe-Hfb5DT_XAbxdb2HqQJHmG-VB-EQ-yoRgk6zo6URlWLNiRaEimhph2ZoJiLQsmrnsv5_0t41yPp_UeocVTuuX9i4_IhZ6Decho_dkX8HS4V8s5NKAZbGrYSSPLl0xNYnI2jO8-HczMn59vOA4C6AJ-wj9npdmBSoglyauf8F4xT_AuQfBKfQ'
        self._api_client.set_default_header('Authorization', f'Bearer {access_token}')

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
