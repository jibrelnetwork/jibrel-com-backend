from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.urls import reverse
from django.utils.safestring import mark_safe

from django_banking.admin.base import (
    ActionRequiredDepositWithdrawalOperationModelAdmin,
    BaseDepositWithdrawalOperationModelAdmin
)
from django_banking.admin.helpers import (
    empty_value_display,
    get_link_tag
)
from django_banking.models.transactions.models import (
    OperationConfirmationDocument
)

from ..models import (
    ColdBankAccount,
    DepositWireTransferOperation,
    RefundWireTransferOperation,
    WithdrawalWireTransferOperation
)
from ..signals import (
    wire_transfer_deposit_approved,
    wire_transfer_deposit_rejected,
    wire_transfer_withdrawal_approved,
    wire_transfer_withdrawal_rejected
)
from .forms import DepositBankAccountForm


@admin.register(ColdBankAccount)
class DepositBankAccountAdmin(admin.ModelAdmin):
    form = DepositBankAccountForm
    list_display = (
        'account_asset',
        'is_active',
        'bank_name',
        'holder_name',
    )
    list_filter = (
        'is_active',
        'account__asset__symbol',
    )
    fieldsets = (
        (None, {
            'fields': (
                'is_active',
                'asset',
                'holder_name',
                'iban_number',
                'account_number',
                'bank_name',
                'branch_address',
                'swift_code'
            )
        }),
    )

    def account_asset(self, obj):
        return obj.account.asset.symbol

    account_asset.short_description = 'Asset'

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        all_fields = set(flatten_fieldsets(self.fieldsets))
        if obj:
            return all_fields - {'is_active', 'asset'}
        return []


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

    @mark_safe
    @empty_value_display
    def last_confirmation_document(self, obj):
        document = OperationConfirmationDocument.objects.filter(operation=obj).order_by('-created_at').first()
        return document and document.file and get_link_tag(document.file.url, document.file.name)

    def after_commit_hook(self, request, obj):
        wire_transfer_deposit_approved.send(sender=DepositWireTransferOperation, instance=obj, user_ip_address=None)

    def after_cancel_hook(self, request, obj):
        wire_transfer_deposit_rejected.send(sender=DepositWireTransferOperation, instance=obj, user_ip_address=None)


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
        wire_transfer_withdrawal_approved.send(sender=WithdrawalWireTransferOperation, instance=obj)

    def after_cancel_hook(self, request, obj):
        wire_transfer_withdrawal_rejected.send(sender=WithdrawalWireTransferOperation, instance=obj)


@admin.register(RefundWireTransferOperation)
class RefundWireTransferOperationModelAdmin(BaseDepositWithdrawalOperationModelAdmin):
    fields = (
        'uuid',
        'deposit',
        'status',
        'user',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    @mark_safe
    def deposit(self, obj):
        return get_link_tag(
            reverse('admin:wire_transfer_depositwiretransferoperation_change', kwargs={'object_id': obj.deposit_id}),
            obj.deposit_id
        )
