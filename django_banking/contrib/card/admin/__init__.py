from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from django_banking.admin.base import (
    ActionRequiredDepositWithdrawalOperationModelAdmin
)
from django_banking.admin.helpers import (
    empty_value_display,
    force_link_display
)

from ..models import (
    DepositCardOperation,
    RefundCardOperation,
    WithdrawalCardOperation
)


@admin.register(DepositCardOperation)
class DepositCardOperationAdmin(ActionRequiredDepositWithdrawalOperationModelAdmin):
    fields = (
        'uuid',
        'status',
        'user',
        'card_account_id',
        'card_charge_id',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    @empty_value_display
    def card_account_id(self, obj):
        return obj.card_account.uuid

    @empty_value_display
    def card_charge_id(self, obj):
        try:
            return self.charge_checkout.latest('created_at').charge_id
        except ObjectDoesNotExist:
            return None

    @force_link_display()
    def refund_link(self, obj):
        refund = obj.refund
        if not refund:
            return
        return reverse('admin:card_refundcardoperation_change', kwargs={
            'object_id': str(refund.pk)
        }), str(refund.pk)


@admin.register(WithdrawalCardOperation)
class WithdrawCardOperationAdmin(DepositCardOperationAdmin):
    pass


@admin.register(RefundCardOperation)
class RefundCardOperationAdmin(DepositCardOperationAdmin):
    @force_link_display()
    def deposit_link(self, obj):
        return reverse('admin:card_depositcardoperation_change', kwargs={
            'object_id': obj.references['deposit']
        }), obj.references['deposit']
