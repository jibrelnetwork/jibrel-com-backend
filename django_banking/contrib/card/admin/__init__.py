from django.contrib import admin

from django_banking.admin.base import (
    ActionRequiredDepositWithdrawalOperationModelAdmin
)
from django_banking.admin.helpers import empty_value_display

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
        return obj.charge_checkout.values_list('charge_id', flat=True).first()


@admin.register(WithdrawalCardOperation)
class WithdrawCardOperationAdmin(DepositCardOperationAdmin):
    pass


@admin.register(RefundCardOperation)
class RefundCardOperationAdmin(DepositCardOperationAdmin):
    pass
