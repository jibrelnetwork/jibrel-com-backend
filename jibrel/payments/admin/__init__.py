from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django_object_actions import DjangoObjectActions

from django_banking.contrib.wire_transfer.admin import DepositWireTransferOperationModelAdmin \
    as DepositWireTransferOperationModelAdmin_
from django_banking.contrib.wire_transfer.models import (
    WithdrawalWireTransferOperation,
    DepositWireTransferOperation,
    RefundWireTransferOperation,
    UserBankAccount)
from django_banking.models import Operation
from django_banking.models.transactions.enum import OperationStatus
from jibrel.investment.enum import InvestmentApplicationStatus

admin.site.unregister(WithdrawalWireTransferOperation)
admin.site.unregister(DepositWireTransferOperation)


@admin.register(DepositWireTransferOperation)
class DepositWireTransferOperationModelAdmin(DepositWireTransferOperationModelAdmin_):
    change_actions = ('refund',)

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
        if RefundWireTransferOperation.objects.filter(
            status__in=[OperationStatus.HOLD, OperationStatus.COMMITTED],
            references__deposit=obj.pk.hex
        ).exists():
            self.message_user(request, 'Already refunded', messages.ERROR)
            return HttpResponseRedirect(back_url)

        accepted = request.POST.get('confirm', None)
        amount = obj.amount
        if accepted == 'yes':
            self.message_user(request, 'Successfully refunded', messages.SUCCESS)
            obj.create_refund()
            operation = Operation.objects.create_refund(
                deposit=obj,
                amount=amount
            )
            # TODO
            # remove at the next release.
            # deposit should not be referenced as FK to IA
            application = obj.deposited_application
            try:
                operation.commit()
                application.status = InvestmentApplicationStatus.CANCELED
                application.save(update_fields=('status',))
            except Exception as exc:
                operation.cancel()
                raise exc
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
