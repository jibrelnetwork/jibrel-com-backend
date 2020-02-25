import logging

from django.conf import settings

from django_banking.contrib.wire_transfer.api.serializers import (
    ColdBankAccountSerializer
)
from jibrel.celery import app
from jibrel.investment.docusign import DocuSignAPI
from jibrel.investment.enum import (
    InvestmentApplicationAgreementStatus,
    InvestmentApplicationStatus
)
from jibrel.investment.models import (
    InvestmentApplication,
    SubscriptionAgreementTemplate
)
from jibrel.investment.signals import investment_submitted

logger = logging.getLogger(__name__)


@app.task()
def docu_sign_start_task(application_id):
    application = InvestmentApplication.objects.with_draft().filter(
        pk=application_id,
        status=InvestmentApplicationStatus.DRAFT,
        subscription_agreement_status=InvestmentApplicationAgreementStatus.INITIAL,
    ).first()
    if not application:
        logger.warning('Draft application with Initial agreement status with id %s was not found', application_id)
        return

    application.subscription_agreement_status = InvestmentApplicationAgreementStatus.PREPARING
    application.save()
    try:
        template = SubscriptionAgreementTemplate.objects.get(offering=application.offering, is_active=True)
        kyc = application.user.profile.last_kyc.details
        signer_data = {
            'signer_email': application.user.email,
            'signer_name': f'{kyc.first_name} {kyc.last_name}',
            'signer_user_id': str(application.user.pk),
        }
        api = DocuSignAPI()
        envelope_id = api.create_envelope(
            template_id=str(template.template_id),
            custom_fields=template.get_context(application),
            **signer_data,
        )
        url = api.create_recipient_view(
            envelope_id=envelope_id,
            return_url=settings.DOCUSIGN_RETURN_URL_TEMPLATE.format(
                application_id=str(application.pk),
            ),
            **signer_data,
        )
        application.prepare_subscription_agreement(
            template=template,
            envelope_id=envelope_id,
            redirect_url=url,
        )
    except Exception as exc:
        InvestmentApplication.objects.with_draft().filter(
            pk=application_id
        ).update(
            subscription_agreement_status=InvestmentApplicationAgreementStatus.ERROR
        )
        logger.exception('Exception was occurred with application %s', application_id)
        raise exc


@app.task()
def docu_sign_finish_task(application_id):
    application = InvestmentApplication.objects.with_draft().filter(
        pk=application_id,
        status=InvestmentApplicationStatus.DRAFT,
        subscription_agreement_status=InvestmentApplicationAgreementStatus.PREPARED,
    ).first()
    if not application:
        logger.warning('Draft application with Prepared agreement status with id %s was not found', application_id)
        return
    application.start_validating_subscription_agreement()
    # todo application created a long time ago might be declined
    try:
        api = DocuSignAPI()
        envelope_status = api.get_envelope_status(str(application.agreement.envelope_id))
        application.finish_subscription_agreement(envelope_status)
        if application.is_agreed_subscription:
            investment_submitted.send(
                sender=application.__class__,
                instance=application,
                asset=application.bank_account.account.asset,
                depositReferenceCode=application.deposit_reference_code,
                **ColdBankAccountSerializer(application.bank_account).data,
            )
    except Exception as exc:
        InvestmentApplication.objects.with_draft().filter(
            pk=application_id
        ).update(
            subscription_agreement_status=InvestmentApplicationAgreementStatus.ERROR
        )
        logger.exception('Exception was occurred with application %s', application_id)
        raise exc
