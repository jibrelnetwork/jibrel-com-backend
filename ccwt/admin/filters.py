from django.contrib import admin

from jibrel.accounting.models import Asset


class AssetListFilter(admin.SimpleListFilter):
    title = 'Asset'
    parameter_name = 'asset'

    def lookups(self, request, model_admin):
        return tuple(Asset.objects.values_list('pk', 'symbol'))

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            queryset = queryset.filter(transactions__account__asset_id=value)
        return queryset
