import pytest
from checkout_sdk.common import HTTPResponse
from checkout_sdk.enums import HTTPStatus
from checkout_sdk.payments.responses import PaymentProcessed
from django.test import override_settings

from django_banking.contrib.card.backend.checkout.enum import (
    CheckoutStatus,
    WebhookType
)
from django_banking.contrib.card.backend.checkout.models import CheckoutCharge
from django_banking.models.transactions.enum import (
    OperationMethod,
    OperationStatus
)
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.payments.tasks import checkout_request
from tests.test_payments.utils import validate_response_schema


def payment_stub(user, application, http_status=HTTPStatus.CREATED, **kwargs):
    data = {
        "id": "pay_mbabizu24mvu3mela5njyhpit4",
        "action_id": "act_mbabizu24mvu3mela5njyhpit4",
        "approved": True,
        "amount": int(application.amount * 100),
        "currency": "USD",
        "status": "Captured",
        "reference": application.deposit_reference_code,
        "customer": {
            "id": "cus_udst2tfldj6upmye2reztkmm4i",
            "email": user.email,
            "name": str(user.profile.last_kyc.details)
        },
    }
    data.update(kwargs)
    return HTTPResponse(http_status, {}, data, 1)


def create_investment_deposit(client, application, token=None):
    url = f'/v1/investment/applications/{application.pk}/deposit/card'
    response = client.post(url, {
        'cardToken': token or f'tok_{"a"*26}'
    })
    return response


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.parametrize(
    'checkout_status, deposit_status, application_status',
    (
        (CheckoutStatus.CAPTURED, OperationStatus.COMMITTED, InvestmentApplicationStatus.HOLD),
        (CheckoutStatus.PENDING, OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.AUTHORIZED, OperationStatus.HOLD, InvestmentApplicationStatus.HOLD),
        (CheckoutStatus.CANCELLED, OperationStatus.CANCELLED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.DECLINED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.PAID, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.VERIFIED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.VOIDED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.PARTIALLY_CAPTURED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.REFUNDED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (CheckoutStatus.PARTIALLY_REFUNDED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
    )
)
@pytest.mark.django_db
def test_create_deposit(client, full_verified_user, application_factory,
                        mocker, checkout_status, deposit_status, application_status):
    client.force_login(full_verified_user)
    application = application_factory()
    mocker.patch('jibrel.payments.tasks.checkout_request.delay', side_effect=checkout_request)
    # full response here:
    # https://api-reference.checkout.com/#tag/Payments/paths/~1payments/post
    data = {
        'status': checkout_status
    }
    mock = mocker.patch('checkout_sdk.checkout_api.PaymentsClient._send_http_request',
                        return_value=payment_stub(full_verified_user, application, **data))
    response = create_investment_deposit(client, application)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/applications/{applicationId}/deposit/card', 'POST', response)
    application.refresh_from_db()
    # should update immediately
    assert application.deposit is not None
    assert application.deposit.amount == application.amount
    assert application.deposit.status == deposit_status
    assert application.deposit.charge_checkout.first().payment_status == checkout_status
    assert application.status == application_status
    mock.assert_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_auth(client, application_factory):
    application = application_factory()
    url = f'/v1/investment/applications/{application.pk}/deposit/card'
    response = client.post(url)
    assert response.status_code == 403


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_deposit_3ds(client, full_verified_user, application_factory, mocker):
    client.force_login(full_verified_user)
    application = application_factory(status=InvestmentApplicationStatus.DRAFT)
    mocker.patch('jibrel.payments.tasks.checkout_request.delay', side_effect=checkout_request)
    # full response here:
    # https://api-reference.checkout.com/#tag/Payments/paths/~1payments/post
    action_required = 'https://www.youtube.com/?gl=RU&hl=ru'
    data = {
        "status": CheckoutStatus.PENDING,
        "_links": {
            "redirect": {
                "href": action_required
            }
        }
    }
    mocker.patch(
        'checkout_sdk.checkout_api.PaymentsClient._send_http_request',
        return_value=payment_stub(full_verified_user, application, http_status=HTTPStatus.ACCEPTED, **data)
    )
    response = create_investment_deposit(client, application)
    assert response.status_code == 201
    validate_response_schema('/v1/investment/applications/{applicationId}/deposit/card', 'POST', response)
    application.refresh_from_db()
    assert application.deposit.status == OperationStatus.ACTION_REQUIRED
    operation_response = client.get(f'/v1/payments/operations/{response.data["data"]["depositId"]}/')
    assert operation_response.status_code == 200
    assert operation_response.data["data"]["depositReferenceCode"] == application.deposit_reference_code
    assert operation_response.data["data"]["charge"]["actionUrl"] == action_required


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
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
def test_create_deposit_already_funded(client, full_verified_user, application_factory,
                                       create_deposit_operation, asset_usd,
                                       deposit_status, expected_status):
    client.force_login(full_verified_user)
    application = application_factory(status=InvestmentApplicationStatus.DRAFT)
    application.deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17,
        method=OperationMethod.CARD
    )
    application.deposit.status = deposit_status
    application.deposit.save()
    application.save()
    response = create_investment_deposit(client, application)
    assert response.status_code == expected_status


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_deposit_already_hold(client, full_verified_user, application_factory):
    client.force_login(full_verified_user)
    application = application_factory(status=InvestmentApplicationStatus.HOLD)
    response = create_investment_deposit(client, application)
    assert response.status_code == 409


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_deposit_token_bad(client, full_verified_user, application_factory):
    client.force_login(full_verified_user)
    application = application_factory()
    response = create_investment_deposit(client, application, f'blablba')
    assert response.status_code == 400


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_deposit_token_used(client, full_verified_user, application_factory,
                        asset_usd, create_deposit_operation):
    client.force_login(full_verified_user)
    application = application_factory()
    deposit = create_deposit_operation(
        user=full_verified_user,
        asset=asset_usd,
        amount=17,
        method=OperationMethod.CARD
    )
    deposit.references['checkout_token'] = f'tok_{"a"*26}'
    deposit.save()
    response = create_investment_deposit(client, application, deposit.references['checkout_token'])
    assert response.status_code == 400


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_deposit_token_expired(client, full_verified_user, application_factory,
                        offering, mocker, cold_bank_account_factory):
    pass


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.parametrize(
    'create_charge',
    (True, False)
)
@pytest.mark.parametrize(
    'event_type, checkout_status, deposit_status, application_status',
    (
        (WebhookType.PAYMENT_CAPTURED, CheckoutStatus.CAPTURED, OperationStatus.COMMITTED, InvestmentApplicationStatus.HOLD),
        (WebhookType.PAYMENT_PENDING, CheckoutStatus.PENDING, OperationStatus.ACTION_REQUIRED, InvestmentApplicationStatus.PENDING),
        (WebhookType.PAYMENT_APPROVED, CheckoutStatus.AUTHORIZED, OperationStatus.HOLD, InvestmentApplicationStatus.HOLD),
        (WebhookType.PAYMENT_CANCELED, CheckoutStatus.CANCELLED, OperationStatus.CANCELLED, InvestmentApplicationStatus.PENDING),
        (WebhookType.PAYMENT_DECLINED, CheckoutStatus.DECLINED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (WebhookType.PAYMENT_EXPIRED, CheckoutStatus.DECLINED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (WebhookType.PAYMENT_VOIDED, CheckoutStatus.VOIDED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
        (WebhookType.PAYMENT_CAPTURE_DECLINED, CheckoutStatus.DECLINED, OperationStatus.DELETED, InvestmentApplicationStatus.PENDING),
    )
)
@pytest.mark.django_db
def test_create_deposit_webhook(client, full_verified_user, application_factory,
                                mocker, asset_usd,
                                create_charge,
                                event_type, checkout_status, deposit_status, application_status):
    mocker.patch('jibrel.payments.permissions.CheckoutHMACSignature.has_permission',
                    return_value=True)
    application = application_factory()
    application.create_deposit(
        asset_usd,
        application.amount,
        references={
            'reference_code': application.deposit_reference_code
        },
        method=OperationMethod.CARD,
        hold=False,
        commit=True
    )
    if create_charge:
        payment = PaymentProcessed(
            payment_stub(full_verified_user, application,
                         status=CheckoutStatus.PENDING)
        )
        charge = CheckoutCharge.objects.create(
            user=full_verified_user,
            payment=payment,
            operation=application.deposit
        )
        charge.update_deposit_status()

    mocker.patch('jibrel.payments.tasks.checkout_request.delay', side_effect=checkout_request)
    stub = payment_stub(full_verified_user, application, status=checkout_status)
    # full response here:
    # https://api-reference.checkout.com/#tag/Payments/paths/~1payments/post
    mock = mocker.patch('checkout_sdk.checkout_api.PaymentsClient._send_http_request',
                        return_value=stub)
    response = client.post(
        '/v1/payments/webhook/checkout',
        {
            'type': event_type,
            'data': stub.body
        },
        content_type='application/json'
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.deposit is not None
    assert application.deposit.amount == application.amount
    assert application.deposit.status == deposit_status
    assert application.deposit.charge_checkout.first().payment_status == checkout_status
    assert application.status == application_status
    mock.assert_called() if not create_charge else mock.assert_not_called()


@override_settings(DJANGO_BANKING_CARD_BACKEND='django_banking.contrib.card.backend.checkout')
@pytest.mark.django_db
def test_create_refund_webhook_(client, full_verified_user, application_factory,
                        offering, mocker, cold_bank_account_factory):
    # TODO
    pass
