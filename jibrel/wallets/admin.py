from django.contrib import admin
from .models import (
    Wallet,
    NotableAddresses,
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'address', 'version_number', 'deleted')
    readonly_fields = ('uid', 'name', 'address', 'mnemonic', 'public_key', 'version_number', 'derivation_path', 'user')
    search_fields = ['uid', 'address', 'user__email']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotableAddresses)
class NotableAddressesAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'address')
    search_fields = ['name', 'address']
