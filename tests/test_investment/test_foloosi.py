import itertools
from uuid import uuid4

import pytest
from django.test import override_settings

from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI
from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus
from django_banking.models.transactions.enum import (
    OperationMethod,
    OperationStatus
)
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.payments.tasks import (
    foloosi_request,
    foloosi_update,
    foloosi_update_all
)
from tests.test_payments.utils import validate_response_schema

create_stub = {
    "reference_token":
        "U0sjdGVzdF8kMnkkMTAkM21LRi0xZGliVDhldTV4NHlZSm9tZXZobnZxWTNEVnZmay1MdHNndTNFenNBTDU0clhWYkccVE4jRkxTQVBJNWM3Njk2ZDkwOWIzNxxSVCMkMnkkMTAkQXZ4ay9wdjlpTFlYLzRSZ2FjSkxpZWhHb2o0U0wvTFpZNXAyVjRGOVFycWNQZ2lHQ3VEZ08=",
    "payment_qr_data":
        "UEgjNTgcQU0jMTMwHE9GRiMcUFJPTU8jHERFUyNNYWRlIHBheW1lbnQgdG8gT00tTWVyY2hhbnQgKFRlc3QpHEFWX3YxOkZSTV9NHFBLIyQyeSQxMCR2RWRIMVZpSHBLV2lSNmxEdE9IUUFPM2RabTZheFlBLmQ2LWdXNUEubXNvQWJPLks1ZjduRxxJUCMcTUFDIxxTVUIjMBxDT0RFIw==",
    "payment_qr_url":
        "https://chart.googleapis.com/chart?cht=qr&chs=400x400&chl=UEgjNTgcQU0jMTMwHE9GRiMcUFJPTU8jHERFUyNNYWRlIHBheW1lbnQgdG8gT00tTWVyY2hhbnQgKFRlc3QpHEFWX3YxOkZSTV9NHFBLIyQyeSQxMCR2RWRIMVZpSHBLV2lSNmxEdE9IUUFPM2RabTZheFlBLmQ2LWdXNUEubXNvQWJPLks1ZjduRxxJUCMcTUFDIxxTVUIjMBxDT0RFIw=="
}


def list_stub(user, application, pages, limit=100):
    stub = payment_stub(user, application, status=FoloosiStatus.CAPTURED)
    return [[{
        **stub,
        'transaction_no': str(uuid4()),
        'optional1': str(uuid4()),
    } for i in range(limit)] for i_ in range(pages)] + [[]]


def detail_stub(application, **kwargs):
    data = {
        'status': 'success',
        'transaction_no': 'TESTDFLSAPI191145e6a2cd232505',
        "optional1": str(application.deposit.pk),
        "optional2": application.deposit_reference_code,
    }
    data.update(kwargs)
    return data


def payment_stub(user, application, **kwargs):
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


def create_investment_deposit(client, application, token=None):
    url = f'/v1/investment/applications/{application.pk}/deposit/card'
    response = client.post(url, {})
    return response


@pytest.fixture()
def application_with_investment_deposit(full_verified_user, application_factory, asset_usd,
                                        create_deposit_operation, mocker):
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
                     return_value=create_stub)
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


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_create_deposit(client, full_verified_user, application_factory,
                        mocker):
    client.force_login(full_verified_user)
    application = application_factory(status=InvestmentApplicationStatus.PENDING)
    mocker.patch('jibrel.payments.tasks.foloosi_request.delay', side_effect=foloosi_request)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                        return_value=create_stub)
    response = create_investment_deposit(client, application)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/applications/{applicationId}/deposit/card', 'POST', response)
    application.refresh_from_db()
    # should update immediately
    assert application.deposit is not None
    assert application.deposit.amount == application.amount
    assert application.deposit.status == OperationStatus.ACTION_REQUIRED
    assert application.deposit.charge.payment_status == FoloosiStatus.PENDING
    assert application.deposit.charge.reference_token == create_stub['reference_token']
    assert application.status == InvestmentApplicationStatus.PENDING
    mock.assert_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_auth(client, application_factory):
    application = application_factory()
    url = f'/v1/investment/applications/{application.pk}/deposit/card'
    response = client.post(url)
    assert response.status_code == 403


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.parametrize(
    'deposit_status, expected_status',
    (
        (OperationStatus.COMMITTED, 409),
        (OperationStatus.HOLD, 409),
        (OperationStatus.CANCELLED, 201),
        (OperationStatus.DELETED, 201),
        (OperationStatus.ACTION_REQUIRED, 409),
    )
)
@pytest.mark.django_db
def test_create_deposit_already_funded(client, full_verified_user, application_with_investment_deposit,
                                       deposit_status, expected_status, mocker):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING,
                                                      deposit_status=deposit_status)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                        return_value=detail_stub(application))
    response = create_investment_deposit(client, application)
    assert response.status_code == expected_status
    if expected_status == 409:
        mock.assert_not_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_create_deposit_already_hold(client, full_verified_user, application_with_investment_deposit,
                                     mocker):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.HOLD)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                 return_value=detail_stub(application))
    response = create_investment_deposit(client, application)
    assert response.status_code == 409
    mock.assert_not_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.parametrize(
    'transaction_id_persist',
    (True, False)
)
@pytest.mark.parametrize(
    'foloosi_status, deposit_status, application_status',
    (
        (FoloosiStatus.CAPTURED, OperationStatus.COMMITTED, InvestmentApplicationStatus.HOLD),
        (FoloosiStatus.PENDING, OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        ('failed', OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        ('refund', OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
    )
)
@pytest.mark.django_db
def test_get_deposit_details(client, full_verified_user,
                                mocker, application_with_investment_deposit,
                                transaction_id_persist,
                                foloosi_status, deposit_status, application_status):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)
    charge = application.deposit.charge
    stub = payment_stub(full_verified_user, application, status=foloosi_status)
    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             return_value=[stub])
    mock_get = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                             return_value=detail_stub(application, status=foloosi_status))
    if transaction_id_persist:
        charge.charge_id = stub['transaction_no']
        charge.save()

    mocker.patch('jibrel.payments.tasks.foloosi_update.delay', side_effect=foloosi_update)
    response = client.get(
        f'/v1/payments/operations/{str(application.deposit.pk)}'
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.deposit is not None
    assert application.deposit.amount == application.amount
    assert application.deposit.status == deposit_status
    if foloosi_status == FoloosiStatus.CAPTURED:
        assert application.deposit.charge.payment_status == foloosi_status
        assert application.deposit.charge.charge_id == stub['transaction_no']
        mock_get.assert_called()
    else:
        assert application.deposit.charge.payment_status == FoloosiStatus.PENDING

    assert application.status == application_status
    if transaction_id_persist:
        mock_list.assert_not_called()
    else:
        mock_list.assert_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_get_deposit_details_pagination(full_verified_user, application_with_investment_deposit,
                                        mocker):
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)

    pages = 3
    stubs = list_stub(full_verified_user, application, pages)
    stubs[pages-1][99]['optional1'] = str(application.deposit_id)
    stubs[pages-1][99]['optional2'] = application.deposit_reference_code

    mock_get = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.get',
                            side_effect=list(itertools.chain(*stubs)))
    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             side_effect=stubs)
    payment = FoloosiAPI().get_by_reference_code(str(application.deposit_id))
    assert mock_list.call_count == pages
    assert mock_get.call_count == pages * 100
    assert payment['transaction_no'] == stubs[pages-1][99]['transaction_no']
    assert payment['optional1'] == str(application.deposit_id)
    assert payment['optional2'] == application.deposit_reference_code


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.parametrize(
    'foloosi_status, deposit_status, application_status',
    (
        (FoloosiStatus.CAPTURED, OperationStatus.COMMITTED, InvestmentApplicationStatus.HOLD),
        (FoloosiStatus.PENDING, OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        ('failed', OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        ('refund', OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
    )
)
@pytest.mark.django_db
def test_get_deposit_all(client, full_verified_user, application_with_investment_deposit, mocker,
                         foloosi_status, deposit_status, application_status):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)
    stub = detail_stub(application, status=foloosi_status)

    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             return_value=[stub])
    mock_get = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.get',
                            return_value=stub)
    foloosi_update_all()
    application.refresh_from_db()
    assert application.deposit.amount == application.amount
    assert application.deposit.status == deposit_status
    if foloosi_status == FoloosiStatus.CAPTURED:
        assert application.deposit.charge.payment_status == foloosi_status
        assert application.deposit.charge.charge_id == stub['transaction_no']
        mock_get.assert_called()
    else:
        assert application.deposit.charge.payment_status == FoloosiStatus.PENDING

    mock_list.assert_called()
    assert application.status == application_status


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_get_deposit_all_pagination(client, full_verified_user, application_factory,
                                        mocker):
    application = application_factory(status=InvestmentApplicationStatus.PENDING)
    pages = 3
    stubs = list_stub(full_verified_user, application, pages)
    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             side_effect=stubs)
    payments = FoloosiAPI().all()
    assert mock_list.call_count == pages + 1
    assert len(payments) == pages * 100
