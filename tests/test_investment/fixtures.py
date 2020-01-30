from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from jibrel.campaigns.enum import OfferingStatus
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement
)


@pytest.fixture()
def application_factory(db, full_verified_user, account_factory, offering_factory):
    def _application_factory(amount=17, status=InvestmentApplicationStatus.COMPLETED, offering=None):
        if offering is None:
            offering = offering_factory(
                status=OfferingStatus.ACTIVE,
                date_start=timezone.now() - timedelta(1),
                date_end=timezone.now() + timedelta(1)
            )
        acc1 = account_factory()
        return InvestmentApplication.objects.create(
            offering=offering,
            user=full_verified_user,
            account=acc1,
            amount=amount,
            is_agreed_risks=True,
            is_agreed_subscription=True,
            status=status
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
