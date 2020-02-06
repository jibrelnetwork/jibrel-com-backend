from django.contrib import (
    admin,
    messages
)
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

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

admin.site.unregister(WithdrawalWireTransferOperation)
admin.site.unregister(DepositWireTransferOperation)
admin.site.unregister(RefundWireTransferOperation)


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
    change_actions = ('refund',)
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

    def get_change_actions(self, request, object_id, form_url):
        obj = self.get_queryset(request).filter(pk=object_id).first()
        if obj and obj.status == OperationStatus.COMMITTED:
            return ('refund',)
        return super().get_change_actions(request, object_id, form_url)

    def refund(self, request, obj):
        # TODO find a better solution
        # as soon as obj is not get with amount. get it again
        obj = self.get_queryset(request).with_amount().filter(pk=obj.pk).first()

        back_url = reverse(
            f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
            kwargs={'object_id': obj.pk}
        )
        if not obj.is_committed:
            self.message_user(request, 'Operation must be committed first', messages.ERROR)
            return HttpResponseRedirect(back_url)

        if obj.refund:
            self.message_user(request, 'Already refunded', messages.ERROR)
            return HttpResponseRedirect(back_url)

        accepted = request.POST.get('confirm', None)
        amount = obj.amount
        if accepted == 'yes':
            operation = Operation.objects.create_refund(
                deposit=obj,
                amount=amount
            )
            try:
                operation.commit()
                # TODO
                # remove at the next release.
                # deposit should not be referenced as FK to IA
                obj.deposited_application.all().select_for_update().update(
                    status=InvestmentApplicationStatus.CANCELED
                )
            except Exception as exc:
                operation.cancel()
                raise exc
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
