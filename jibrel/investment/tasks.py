from django.conf import settings

from django_banking.contrib.wire_transfer.api.serializers import (
    ColdBankAccountSerializer
)
from jibrel.celery import app
from jibrel.investment.docusign import DocuSignAPI
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import (
    InvestmentApplication,
    SubscriptionAgreementTemplate
)
from jibrel.investment.signals import investment_submitted


@app.task()
def docu_sign_start_task(application_id):
    application = InvestmentApplication.objects.with_draft().filter(pk=application_id).first()
    if application.is_agreed_subscription or application.is_agreement_created:
        return

    template = SubscriptionAgreementTemplate.objects.get(offering=application.offering)
    kyc = application.user.profile.last_kyc.details
    signer_data = {
        'signer_email': application.user.email,
        'signer_name': f'{kyc.first_name} {kyc.last_name}',
        'signer_user_id': str(application.user.pk),
    }
    api = DocuSignAPI()
    envelope = api.create_envelope(
        template_id=str(template.template_id),
        **signer_data,
    )
    view = api.create_recipient_view(
        envelope_id=envelope.envelope_id,
        return_url=settings.DOCU_SIGN_RETURN_URL_TEMPLATE.format(
            application_id=str(application.pk),
        ),
        **signer_data,
    )
    application.prepare_subscription_agreement(
        template=template,
        envelope_id=envelope.envelope_id,
        status=envelope.status,
        redirect_url=view.url,
    )


@app.task()
def docu_sign_finish_task(application_id):
    application = InvestmentApplication.objects.with_draft().filter(
        pk=application_id,
        status=InvestmentApplicationStatus.DRAFT,
    )
    if application.is_agreed_subscription:
        return
    # todo application created a long time ago might be declined
    api = DocuSignAPI()
    envelope = api.get_envelope(str(application.agreement.envelope_id))
    application.finish_subscription_agreement(envelope.envelope_id)
    if application.is_agreed_subscription:
        investment_submitted.send(
            sender=application.__class__,
            instance=application,
            asset=application.bank_account.account.asset,
            depositReferenceCode=application.deposit_reference_code,
            **ColdBankAccountSerializer(application.bank_account).data,
        )
