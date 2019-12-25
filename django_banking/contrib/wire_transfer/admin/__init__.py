from django.contrib import admin
from django.utils.safestring import mark_safe

from django_banking.admin.base import ActionRequiredDepositWithdrawalOperationModelAdmin
from django_banking.admin.helpers import empty_value_display
from django_banking.models.transactions.models import OperationConfirmationDocument
from django_banking.admin.helpers import get_link_tag
from .forms import DepositBankAccountForm
from ..models import DepositBankAccount, DepositWireTransferOperation, WithdrawalWireTransferOperation
from ..signals import (
    wire_transfer_deposit_approved,
    wire_transfer_deposit_rejected,
    wire_transfer_withdrawal_approved,
    wire_transfer_withdrawal_rejected
)


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
        wire_transfer_deposit_approved.send(sender=DepositWireTransferOperation, instance=obj)

    def after_cancel_hook(self, request, obj):
        wire_transfer_deposit_rejected.send(sender=DepositWireTransferOperation, instance=obj)


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
