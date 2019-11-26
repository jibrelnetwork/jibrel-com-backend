import json

from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from jibrel.core.common.helpers import (
    force_empty_value_display,
    get_link_tag
)
from jibrel.payments.models import (
    DepositCardOperation,
    DepositCryptoAccount,
    DepositCryptoOperation,
    DepositWireTransferOperation,
    WithdrawalCardOperation,
    WithdrawalCryptoOperation,
    WithdrawalWireTransferOperation
)
from jibrel_admin.celery import (
    send_fiat_deposit_approved_mail,
    send_fiat_deposit_rejected_mail,
    send_fiat_withdrawal_approved_mail,
    send_fiat_withdrawal_rejected_mail
)
from jibrel.accounting.exceptions import (
    AccountBalanceException,
    OperationBalanceException
)
from jibrel.accounting.models import Account
from jibrel.payments.models import (
    DepositBankAccount,
    Fee,
    OperationConfirmationDocument
)

from .filters import AssetListFilter
from .forms import (
    DepositBankAccountForm,
    DepositCryptoAccountForm,
    DepositCryptoOperationForm,
    WithdrawalCryptoOperationForm
)


@admin.register(DepositCryptoAccount)
class DepositCryptoAccountAdmin(DjangoObjectActions, admin.ModelAdmin):
    change_list_template = 'fix_change_list.html'
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
                'type': Account.TYPE_PASSIVE,
                'strict': True
            }

            accounts = []
            for a in addresses:
                account = Account.objects.create(asset_id=a['asset'], **account_data)
                accounts.append(
                    DepositCryptoAccount(address=a['address'], account=account)
                )
            DepositCryptoAccount.objects.bulk_create(accounts)
            return redirect('admin:payments_depositcryptoaccount_changelist')
        return render(request, template_name='crypto_accounts_via_json.html')

    changelist_actions = ['add_via_json']


@admin.register(DepositBankAccount)
class DepositBankAccountAdmin(admin.ModelAdmin):
    form = DepositBankAccountForm
    list_display = (
        'asset_country',
        'account_asset',
        'is_active',
        'bank_account_details',
    )
    list_filter = (
        'is_active',
        'account__asset__country'
    )

    def asset_country(self, obj):
        return obj.account.asset.country

    asset_country.short_description = 'Country'

    def account_asset(self, obj):
        return obj.account.asset.symbol

    account_asset.short_description = 'Asset'

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
        return obj.user.uuid

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


empty_value_display = force_empty_value_display(BaseDepositWithdrawalOperationModelAdmin.empty_value_display)


class ActionRequiredDepositWithdrawalOperationModelAdmin(DjangoObjectActions, BaseDepositWithdrawalOperationModelAdmin):
    change_actions = ('commit', 'cancel',)

    def get_change_actions(self, request, object_id, form_url):
        # actually get_object fires twice
        if self.get_object(request, object_id).status in (self.model.NEW, self.model.HOLD):
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


@admin.register(DepositWireTransferOperation)
class DepositWireTransferOperationModelAdmin(ActionRequiredDepositWithdrawalOperationModelAdmin):
    fields = (
        'uuid',
        'status',
        'user',
        'bank_name',
        'holder_name',
        'iban_number',
        'last_confirmation_document',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    def reference_code(self, obj):
        return obj.references.get('reference_code')

    @empty_value_display
    def swift_code(self, obj):
        return obj.bank_account and obj.bank_account.swift_code

    @empty_value_display
    def bank_name(self, obj):
        return obj.bank_account and obj.bank_account.bank_name

    @empty_value_display
    def holder_name(self, obj):
        return obj.bank_account and obj.bank_account.holder_name

    @empty_value_display
    def iban_number(self, obj):
        return obj.bank_account and obj.bank_account.iban_number

    @empty_value_display
    def last_confirmation_document(self, obj):
        document = OperationConfirmationDocument.objects.filter(operation=obj).order_by('-created_at').first()
        return document and document.file and mark_safe(get_link_tag(document.file.url, document.file.name))

    def after_commit_hook(self, request, obj):
        send_fiat_deposit_approved_mail(obj.user.pk)

    def after_cancel_hook(self, request, obj):
        send_fiat_deposit_rejected_mail(obj.user.pk)


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


@admin.register(WithdrawalWireTransferOperation)
class WithdrawalWireTransferOperationModelAdmin(DepositWireTransferOperationModelAdmin):
    fields = (
        'uuid',
        'status',
        'user',
        'swift_code',
        'bank_name',
        'holder_name',
        'iban_number',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    def after_commit_hook(self, request, obj):
        send_fiat_withdrawal_approved_mail(obj.user.pk)

    def after_cancel_hook(self, request, obj):
        send_fiat_withdrawal_rejected_mail(obj.user.pk, obj.pk)


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


@admin.register(WithdrawalCardOperation)
class WithdrawCardOperationAdmin(DepositCardOperationAdmin):
    pass


@admin.register(Fee)
class FeeModelAdmin(admin.ModelAdmin):
    list_display = (
        'operation_type',
        'value_type',
        'value',
        'asset',
    )

    ordering = ('operation_type',)

    def has_change_permission(self, request, obj=None):
        # Active superusers have all permissions.
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Active superusers have all permissions.
        return request.user.is_superuser

    def has_add_permission(self, request):
        # Active superusers have all permissions.
        return request.user.is_superuser
