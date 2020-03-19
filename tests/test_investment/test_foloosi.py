import itertools

import pytest
from django.test import override_settings

from django_banking.contrib.card.backend.foloosi.backend import FoloosiAPI
from django_banking.contrib.card.backend.foloosi.enum import FoloosiStatus
from django_banking.models.transactions.enum import OperationStatus
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.payments.tasks import (
    foloosi_request,
    foloosi_update,
    foloosi_update_all
)
from tests.test_payments.utils import validate_response_schema


def create_investment_deposit(client, application, token=None):
    url = f'/v1/investment/applications/{application.pk}/deposit/card'
    response = client.post(url, {})
    return response


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_create_deposit(client, full_verified_user, application_factory,
                        foloosi_create_stub,
                        mocker):
    client.force_login(full_verified_user)
    application = application_factory(status=InvestmentApplicationStatus.PENDING)
    mocker.patch('jibrel.payments.tasks.foloosi_request.delay', side_effect=foloosi_request)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                        return_value=foloosi_create_stub)
    response = create_investment_deposit(client, application)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/applications/{applicationId}/deposit/card', 'POST', response)
    application.refresh_from_db()
    # should update immediately
    assert application.deposit is not None
    assert application.deposit.amount == application.amount
    assert application.deposit.status == OperationStatus.ACTION_REQUIRED
    assert application.deposit.charge.payment_status == FoloosiStatus.PENDING
    assert application.deposit.charge.reference_token == foloosi_create_stub['reference_token']
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
                                       deposit_status, expected_status, foloosi_detail_stub,
                                       mocker):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING,
                                                      deposit_status=deposit_status)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                        return_value=foloosi_detail_stub(application))
    response = create_investment_deposit(client, application)
    assert response.status_code == expected_status
    if expected_status == 409:
        mock.assert_not_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.foloosi')
@pytest.mark.django_db
def test_create_deposit_already_hold(client, full_verified_user, application_with_investment_deposit,
                                     foloosi_detail_stub,
                                     mocker):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.HOLD)
    mock = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                 return_value=foloosi_detail_stub(application))
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
                                transaction_id_persist, foloosi_detail_stub,
                                foloosi_payment_stub,
                                foloosi_status, deposit_status, application_status):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)
    charge = application.deposit.charge
    stub = foloosi_payment_stub(full_verified_user, application, status=foloosi_status)
    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             return_value=[stub])
    mock_get = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI._dispatch',
                             return_value=foloosi_detail_stub(application, status=foloosi_status))
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
                                        foloosi_list_stub,
                                        mocker):
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)

    pages = 3
    stubs = foloosi_list_stub(full_verified_user, application, pages)
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
                         foloosi_status, deposit_status,
                         foloosi_detail_stub,
                         application_status):
    client.force_login(full_verified_user)
    application = application_with_investment_deposit(status=InvestmentApplicationStatus.PENDING)
    stub = foloosi_detail_stub(application, status=foloosi_status)

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
                                    foloosi_list_stub,
                                    mocker):
    application = application_factory(status=InvestmentApplicationStatus.PENDING)
    pages = 3
    stubs = foloosi_list_stub(full_verified_user, application, pages)
    mock_list = mocker.patch('django_banking.contrib.card.backend.foloosi.backend.FoloosiAPI.list',
                             side_effect=stubs)
    payments = FoloosiAPI().all()
    assert mock_list.call_count == pages + 1
    assert len(payments) == pages * 100
