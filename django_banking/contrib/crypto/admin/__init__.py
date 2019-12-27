import json

from django.contrib import admin
from django.db import transaction
from django.shortcuts import (
    redirect,
    render
)
from django_object_actions import DjangoObjectActions

from django_banking.admin.base import (
    ActionRequiredDepositWithdrawalOperationModelAdmin,
    BaseDepositWithdrawalOperationModelAdmin
)
from django_banking.admin.helpers import empty_value_display
from django_banking.models import Account
from django_banking.models.accounts.enum import AccountType

from ..models import (
    DepositCryptoOperation,
    UserCryptoDepositAccount,
    WithdrawalCryptoOperation
)
from .forms import (
    DepositCryptoAccountForm,
    DepositCryptoOperationForm,
    WithdrawalCryptoOperationForm
)


@admin.register(UserCryptoDepositAccount)
class DepositCryptoAccountAdmin(DjangoObjectActions, admin.ModelAdmin):
    change_list_template = 'admin/depositcryptoaccount/change_list.html'
    form = DepositCryptoAccountForm
    list_display = (
        'address',
        'account_asset',
        'user',
    )
    list_filter = (
        'account__asset',
    )
    search_fields = (
        'user__email',
        'address',
    )
    list_select_related = (
        'account__asset',
        'user',
    )

    def account_asset(self, obj):
        return obj.account.asset.symbol

    account_asset.short_description = 'Asset'

    @transaction.atomic()
    def add_via_json(self, request, queryset):
        if request.method == 'POST':
            addresses = json.load(request.FILES['json'])

            account_data = {
                'type': AccountType.TYPE_PASSIVE,
                'strict': True
            }

            accounts = []
            for a in addresses:
                account = Account.objects.create(asset_id=a['asset'], **account_data)
                accounts.append(
                    UserCryptoDepositAccount(address=a['address'], account=account)
                )
            UserCryptoDepositAccount.objects.bulk_create(accounts)
            return redirect('admin:payments_depositcryptoaccount_changelist')
        return render(request, template_name='admin/depositcryptoaccount/crypto_accounts_via_json.html')

    changelist_actions = ['add_via_json']


@admin.register(DepositCryptoOperation)
class DepositCryptoOperationModelAdmin(BaseDepositWithdrawalOperationModelAdmin):
    form = DepositCryptoOperationForm
    fields = (
        'uuid',
        'status',
        'user',
        'address',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'tx_hash',
        'created_at',
        'updated_at',
    )
    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'tx_hash',
        'created_at',
        'updated_at',
    )

    def get_readonly_fields(self, request, obj=None):
        return (
            'uuid', 'status', 'user', 'asset', 'fee',
            'total_amount', 'created_at', 'updated_at',
        )

    @empty_value_display
    def address(self, obj):
        return obj.deposit_cryptocurrency_address

    def has_add_permission(self, request):
        return True


@admin.register(WithdrawalCryptoOperation)
class WithdrawalCryptoOperationModelAdmin(ActionRequiredDepositWithdrawalOperationModelAdmin,
                                          DepositCryptoOperationModelAdmin):
    form = WithdrawalCryptoOperationForm

    @empty_value_display
    def address(self, obj):
        return obj.cryptocurrency_address

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj) + ('address', 'amount',)

    def after_commit_hook(self, request, obj):
        pass  # todo

    def after_cancel_hook(self, request, obj):
        pass  # todo

    def has_change_permission(self, request, obj=None):
        return True
