from django.contrib import (
    admin,
    messages
)
from django.contrib.admin import helpers
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from django_banking.contrib.card.admin import \
    DepositCardOperationAdmin as DepositCardOperationAdmin_
from django_banking.contrib.card.admin import \
    RefundCardOperationAdmin as RefundCardOperationAdmin_
from django_banking.contrib.card.backend.foloosi.models import FoloosiCharge
from django_banking.contrib.card.models import (
    DepositCardOperation,
    RefundCardOperation,
    WithdrawalCardOperation
)
from django_banking.contrib.wire_transfer.admin import \
    DepositWireTransferOperationModelAdmin as \
    DepositWireTransferOperationModelAdmin_
from django_banking.contrib.wire_transfer.admin import \
    RefundWireTransferOperationModelAdmin as \
    RefundWireTransferOperationModelAdmin_
from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation,
    RefundWireTransferOperation,
    UserBankAccount,
    WithdrawalWireTransferOperation
)
from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationStatus
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.payments.admin.forms import FoloosiFixMatchForm

admin.site.unregister(WithdrawalWireTransferOperation)
admin.site.unregister(DepositWireTransferOperation)
admin.site.unregister(RefundWireTransferOperation)

admin.site.unregister(WithdrawalCardOperation)
admin.site.unregister(DepositCardOperation)
admin.site.unregister(RefundCardOperation)


@admin.register(DepositWireTransferOperation)
class DepositWireTransferOperationModelAdmin(DepositWireTransferOperationModelAdmin_):
    fields = None
    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'created_at',
        'updated_at',
    )
    change_actions = ('commit', 'cancel', 'refund')
    fieldsets = (
        (None, {
            'fields': (
                'uuid',
                'user_link',
                'amount',
                'asset',
                'status',
                'refund_link',
            )
        }),
        (_('Bank account'), {
            'fields': (
                'bank_name',
                'holder_name',
                'iban_number',
                'last_confirmation_document',
            )
        }),
        (_('Important dates'), {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def refund(self, request, obj):
        if 'user_bank_account_uuid' not in (obj.references or {}):
            self.message_user(request, 'Card deposits cannot be refunded yet.', messages.ERROR)
            return

        elif not obj.is_committed:
            self.message_user(request, 'Operation must be committed first', messages.ERROR)
            return

        elif obj.refund:
            self.message_user(request, 'Already refunded', messages.ERROR)
            return

        back_url = reverse(
            f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
            kwargs={'object_id': obj.pk}
        )

        accepted = request.POST.get('confirm', None)
        amount = obj.amount
        if accepted == 'yes':
            Operation.objects.create_refund(
                deposit=obj,
                amount=amount
            )
            self.message_user(request, 'Successfully refunded', messages.SUCCESS)
            return HttpResponseRedirect(back_url)

        bank_account = UserBankAccount.objects.get(pk=obj.references['user_bank_account_uuid'])
        return render(
            request,
            'admin/wire_transfer/depositwiretransferoperation/refund_confirmation.html',
            context={
                'amount': amount,
                'currency': bank_account.account.asset.symbol,
                'bank_name': bank_account.bank_name,
                'holder_name': bank_account.holder_name,
                'swift_code': bank_account.swift_code,
                'iban_number': bank_account.iban_number,
                'back_url': back_url,
            }
        )


@admin.register(RefundWireTransferOperation)
class RefundWireTransferOperationModelAdmin(RefundWireTransferOperationModelAdmin_):
    fields = None
    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (None, {
            'fields': (
                'uuid',
                'user_link',
                'amount',
                'asset',
                'status',
                'deposit_link',
            )
        }),
        (_('Important dates'), {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(DepositCardOperation)
class DepositCardOperationModelAdmin(DepositCardOperationAdmin_):
    fields = None
    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'created_at',
        'updated_at',
    )
    change_actions = ('refund', 'fix_match')
    fieldsets = (
        (None, {
            'fields': (
                'uuid',
                'user_link',
                'amount',
                'asset',
                'status',
                'charge',
                'refund_link',
            )
        }),
        (_('Important dates'), {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def charge(self, obj):
        return f'{obj.charge.charge_id} ({obj.references["card_account"]["type"]})'

    def refund(self, request, obj):
        charge = obj.charge
        if not isinstance(charge, FoloosiCharge):
            return super().refund(request, obj)

        elif not obj.is_committed:
            self.message_user(request, 'Operation must be committed first', messages.ERROR)
            return

        elif obj.refund:
            self.message_user(request, 'Already refunded', messages.ERROR)
            return

        back_url = reverse(
            f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
            kwargs={'object_id': obj.pk}
        )

        accepted = request.POST.get('confirm', None)
        if accepted == 'yes':
            Operation.objects.create_refund(
                deposit=obj,
                amount=obj.amount
            )
            self.message_user(request, 'Successfully refunded', messages.SUCCESS)
            return HttpResponseRedirect(back_url)

        return render(
            request,
            'admin/card/depositcardoperation/refund_confirmation.html',
            context={
                'amount': obj.amount,
                'currency': obj.asset.symbol,
                'backend': obj.references["card_account"]["type"],
                'charge_id': obj.charge.charge_id,
                'back_url': back_url,
            }
        )

    def fix_match(self, request, obj):
        card_backend_type = obj.references.get('card_account', {}).get('type', '')
        if obj.charge and card_backend_type != 'foloosi':
            self.message_user(request, 'Not a foloosi charge, cannot proceed', messages.ERROR)
            return

        return self.render_custom_form(
            request, obj,
            form=FoloosiFixMatchForm,
            instance=obj.charge,
            template='admin/card/depositcardoperation/fix_match.html',
            success_message='Success, please wait patiently for update'
        )


@admin.register(RefundCardOperation)
class RefundCardOperationAdmin(RefundCardOperationAdmin_):
    fields = None
    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'created_at',
        'updated_at',
    )
    change_actions = ('refund',)
    fieldsets = (
        (None, {
            'fields': (
                'uuid',
                'user_link',
                'amount',
                'asset',
                'status',
                'charge',
                'deposit_link',
            )
        }),
        (_('Important dates'), {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
