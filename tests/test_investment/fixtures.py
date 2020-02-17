from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.enum import (
    InvestmentApplicationAgreementStatus,
    InvestmentApplicationStatus,
    SubscriptionAgreementEnvelopeStatus
)
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement,
    SubscriptionAgreement,
    SubscriptionAgreementTemplate
)


@pytest.fixture()
def application_factory(db, full_verified_user_factory, account_factory, offering_factory, cold_bank_account_factory):
    def _application_factory(
        amount=17,
        status=InvestmentApplicationStatus.COMPLETED,
        subscription_agreement_status=InvestmentApplicationAgreementStatus.INITIAL,
        offering=None,
        user=None
    ):
        if offering is None:
            offering = offering_factory(
                status=OfferingStatus.ACTIVE,
                date_start=timezone.now() - timedelta(1),
                date_end=timezone.now() + timedelta(1)
            )
        if user is None:
            user = full_verified_user_factory()
        acc1 = account_factory()
        return InvestmentApplication.objects.create(
            offering=offering,
            user=user,
            account=acc1,
            amount=amount,
            is_agreed_risks=True,
            subscription_agreement_status=subscription_agreement_status,
            status=status,
            bank_account=cold_bank_account_factory()
        )

    return _application_factory


@pytest.fixture()
def personal_agreement_factory(db, full_verified_user, mocker):
    def _personal_agreement_factory(offering, user=full_verified_user):
        aws = mocker.patch('jibrel.core.storages.AmazonS3Storage.save', return_value='test')
        pa = PersonalAgreement.objects.create(
            offering=offering,
            user=user,
            file=ContentFile(b'blabla', 'blabla.pdf')
        )
        aws.assert_called()
        return pa

    return _personal_agreement_factory


@pytest.fixture()
def subscription_agreement_template_factory(db):
    def _subscription_agreement_template_factory(offering):
        return SubscriptionAgreementTemplate.objects.create(
            name='test',
            offering=offering,
            template_id=uuid4(),
        )

    return _subscription_agreement_template_factory


@pytest.fixture()
def subscription_agreement_factory(db, application_factory, subscription_agreement_template_factory):
    def _subscription_agreement_factory(
        application=None,
        template=None,
        envelope_id=None,
        envelope_status=SubscriptionAgreementEnvelopeStatus.COMPLETED,
    ):
        if not application:
            application = application_factory
        if not template:
            template = subscription_agreement_template_factory(application.offering)
        if not envelope_id:
            envelope_id = uuid4()
        return SubscriptionAgreement.objects.create(
            template=template,
            application=application,
            envelope_id=envelope_id,
            envelope_status=envelope_status,
        )

    return _subscription_agreement_factory
