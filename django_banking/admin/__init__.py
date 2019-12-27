from django.contrib import admin

from ..models import Fee
from .filters import AssetListFilter


@admin.register(Fee)
class FeeModelAdmin(admin.ModelAdmin):
    list_display = (
        'operation_type',
        'value_type',
        'value',
        'asset',
    )
    filters = (AssetListFilter,)
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
