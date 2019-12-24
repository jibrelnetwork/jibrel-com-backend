from django.contrib import admin


from ccwt.admin.base import ActionRequiredDepositWithdrawalOperationModelAdmin
from ccwt.admin.helpers import empty_value_display
from ..models import DepositCardOperation, WithdrawalCardOperation


@admin.register(DepositCardOperation)
class DepositCardOperationAdmin(ActionRequiredDepositWithdrawalOperationModelAdmin):
    fields = (
        'uuid',
        'status',
        'user',
        'tap_card_id',
        'tap_charge_id',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    @empty_value_display
    def tap_card_id(self, obj):
        return obj.card_account.uuid

    @empty_value_display
    def tap_charge_id(self, obj):
        return obj.tapcharge_set.values_list('charge_id', flat=True)[0]


@admin.register(WithdrawalCardOperation)
class WithdrawCardOperationAdmin(DepositCardOperationAdmin):
    pass
