from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus
from django_banking.models.transactions.enum import OperationMethod
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
from jibrel.payments.tasks import foloosi_request


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
def subscription_agreement_template(db, subscription_agreement_template_factory, offering):
    return subscription_agreement_template_factory(
        offering=offering
    )


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


@pytest.fixture()
def foloosi_create_stub():
    return {
    "reference_token":
        "U0sjdGVzdF8kMnkkMTAkM21LRi0xZGliVDhldTV4NHlZSm9tZXZobnZxWTNEVnZmay1MdHNndTNFenNBTDU0clhWYkccVE4jRkxTQVBJNWM3Njk2ZDkwOWIzNxxSVCMkMnkkMTAkQXZ4ay9wdjlpTFlYLzRSZ2FjSkxpZWhHb2o0U0wvTFpZNXAyVjRGOVFycWNQZ2lHQ3VEZ08=",
    "payment_qr_data":
        "UEgjNTgcQU0jMTMwHE9GRiMcUFJPTU8jHERFUyNNYWRlIHBheW1lbnQgdG8gT00tTWVyY2hhbnQgKFRlc3QpHEFWX3YxOkZSTV9NHFBLIyQyeSQxMCR2RWRIMVZpSHBLV2lSNmxEdE9IUUFPM2RabTZheFlBLmQ2LWdXNUEubXNvQWJPLks1ZjduRxxJUCMcTUFDIxxTVUIjMBxDT0RFIw==",
    "payment_qr_url":
        "https://chart.googleapis.com/chart?cht=qr&chs=400x400&chl=UEgjNTgcQU0jMTMwHE9GRiMcUFJPTU8jHERFUyNNYWRlIHBheW1lbnQgdG8gT00tTWVyY2hhbnQgKFRlc3QpHEFWX3YxOkZSTV9NHFBLIyQyeSQxMCR2RWRIMVZpSHBLV2lSNmxEdE9IUUFPM2RabTZheFlBLmQ2LWdXNUEubXNvQWJPLks1ZjduRxxJUCMcTUFDIxxTVUIjMBxDT0RFIw=="
}


@pytest.fixture()
def foloosi_list_stub(foloosi_payment_stub):
    def foloosi_list_stub_(user, application, pages, limit=100):
        stub = foloosi_payment_stub(user, application, status=FoloosiStatus.CAPTURED)
        return [[{
            **stub,
            'transaction_no': str(uuid4()),
            'optional1': str(uuid4()),
        } for i in range(limit)] for i_ in range(pages)] + [[]]
    return foloosi_list_stub_


@pytest.fixture()
def foloosi_detail_stub():
    def foloosi_detail_stub_(application, **kwargs):
        data = {
            'status': 'success',
            'transaction_no': 'TESTDFLSAPI191145e6a2cd232505',
            "optional1": str(application.deposit.pk),
            "optional2": application.deposit_reference_code,
        }
        data.update(kwargs)
        return data
    return foloosi_detail_stub_


@pytest.fixture()
def foloosi_payment_stub():
    def foloosi_payment_stub_(user, application, **kwargs):
        data = {
            'id': 25932,
            'transaction_no': 'TESTDFLSAPI191145e6a2cd232505',
            'sender_id': 19114,
            'receiver_id': 17308,
            'payment_link_id': 0,
            'send_amount': 367.3,
            'sender_currency': 'AED',
            'tip_amount': 0,
            'receive_currency': 'AED',
            'special_offer_applied': 'No',
            'sender_amount': 367.3,
            'receive_amount': 367.3,
            'offer_amount': 0,
            'vat_amount': 0.91,
            'transaction_type': 'c-m',
            'poppay_fee': 18.18,
            'transaction_fixed_fee': 0,
            'customer_foloosi_fee': 0,
            'status': 'success',
            'created': '2020-03-12T12:36:34+00:00',
            'api_transaction': {
                'id': 42670,
                'sender_currency': 'USD',
                'payable_amount_in_sender_currency': application.amount,
            },
            'receiver': {
                'id': 17308,
                'name': 'Faizan Jawed',
                'email': 'talal@jibrel.io',
                'business_name': 'Jibrel Limited'
            },
            'sender': {
                'id': 19114,
                'name': str(user.profile.last_kyc.details),
                'email': user.email,
                'business_name': None,
                'phone_number': '234234234234'
            },
        }
        data.update(kwargs)
        return data
    return foloosi_payment_stub_


@pytest.fixture()
def application_with_investment_deposit(full_verified_user, application_factory, asset_usd,
                                        create_deposit_operation, foloosi_create_stub, mocker):
    def application_with_investment_deposit_(
        status=InvestmentApplicationStatus.PENDING,
        deposit_status=None
    ):
        application = application_factory(status=status)
        application.deposit = create_deposit_operation(
            user=full_verified_user,
            asset=asset_usd,
            amount=17,
            method=OperationMethod.CARD,
            references={
                'card_account': {
                    'type': 'foloosi'
                }
            }
        )
        application.save()
        mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                     return_value=foloosi_create_stub)
        foloosi_request(
            deposit_id=application.deposit.pk,
            user_id=full_verified_user.pk,
            amount=application.amount,
            reference_code=application.deposit_reference_code
        )
        application.refresh_from_db()
        if deposit_status:
            application.deposit.status = deposit_status
            application.deposit.save()
        return application
    return application_with_investment_deposit_
