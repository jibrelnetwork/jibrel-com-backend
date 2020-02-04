from django.contrib import (
    admin,
    messages
)
from django_object_actions import DjangoObjectActions

from ..models.accounts.exceptions import AccountBalanceException
from ..models.transactions.enum import OperationStatus
from ..models.transactions.exceptions import OperationBalanceException
from .filters import AssetListFilter


class BaseDepositWithdrawalOperationModelAdmin(admin.ModelAdmin):
    empty_value_display = '-'

    ordering = ('-created_at',)

    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'uuid',
        'transactions__account__useraccount__user__uuid',
        'transactions__account__useraccount__user__email',
    )

    list_filter = (
        'status',
        AssetListFilter
    )

    def get_queryset(self, request):
        return (
            super(BaseDepositWithdrawalOperationModelAdmin, self).get_queryset(request)
                .with_asset()
                .with_fee()
                .with_amount()
               .with_total_amount()
        )

    def amount(self, obj):
        return obj.amount

    def total_amount(self, obj):
        return obj.total_amount

    def fee(self, obj):
        return obj.fee

    def asset(self, obj):
        return obj.asset

    def user(self, obj):
        return obj.user and obj.user.uuid

    def tx_hash(self, obj):
        return obj.metadata.get('tx_hash')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def after_commit_hook(self, request, obj):
        pass

    def after_cancel_hook(self, request, obj):
        pass


class ActionRequiredDepositWithdrawalOperationModelAdmin(DjangoObjectActions, BaseDepositWithdrawalOperationModelAdmin):
    change_actions = ('commit', 'cancel',)

    def get_change_actions(self, request, object_id, form_url):
        obj = self.get_object(request, object_id)
        if obj and obj.status in (OperationStatus.NEW, OperationStatus.HOLD):
            return super().get_change_actions(request, object_id, form_url)
        return ()

    def commit(self, request, obj):
        if obj.is_committed:
            self.message_user(request, 'Confirmed already')
            return
        try:
            obj.commit()
            self.after_commit_hook(request, obj)
            self.message_user(request, 'Operation confirmed')
        except AccountBalanceException:
            self.message_user(request, f'Transition restricted. {AccountBalanceException.reason}', level=messages.ERROR)
        except (OperationBalanceException, AssertionError):
            self.message_user(request, 'Transition restricted.', level=messages.ERROR)

    def cancel(self, request, obj):
        if obj.is_cancelled:
            self.message_user(request, 'Rejected already')
            return
        obj.cancel()
        self.after_cancel_hook(request, obj)
        self.message_user(request, 'Operation rejected')

    commit.label = 'COMMIT'
    cancel.label = 'CANCEL'
