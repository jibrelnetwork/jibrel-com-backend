from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.utils.translation import ugettext_lazy as _

from jibrel.campaigns.admin.forms import (
    OfferingForm,
    SecurityForm
)
from jibrel.campaigns.models import (
    Company,
    Offering,
    Security
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    ordering = ('name',)
    list_display = ('name', 'slug')

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'slug',
            )
        }),
    )


@admin.register(Security)
class SecurityAdmin(admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = SecurityForm
    ordering = ('-created_at',)
    list_display = ('__str__', 'asset')

    fieldsets = (
        (None, {
            'fields': (
                'company',
                'type',
                'asset__symbol'
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Changes is allowed until first exchange operation requested.
        """
        if not obj:
            return []
        all_fields = set(flatten_fieldsets(self.fieldsets))

        # TODO
        # https://code.djangoproject.com/ticket/29682
        return all_fields - {
            'asset__symbol'
        }


@admin.register(Offering)
class OfferingAdmin(admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = OfferingForm
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': (
                'security',
                'round',
                'status'
            )
        }),
        (_('Funding'), {
            'fields': (
                'valuation',
                'goal',
                'shares',
                'price',
            )
        }),
        (_('Limitations'), {
            'fields': (
                'limit_min_share',
                'limit_max_share',
                'date_start',
                'date_end',
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        All money related fields cannot be changed after first exchange operation requested.
        goal and shares can be increased proportionally.
        total valuation and price cannot be changed

        """
        if not obj:
            return ['status']
        return [
            'security',
            'round',
            'valuation',
            'price',
            'date_start',
        ]
