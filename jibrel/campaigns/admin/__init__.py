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
                'goal'
            )
        }),
        (_('Shares'), {
            'fields': (
                'shares',
                'price',
            )
        }),
        (_('Limitations'), {
            'fields': (
                'limit_min_amount',
                'limit_max_amount',
                'date_start',
                'date_end',
            )
        }),
        (_('Applications count'), {
            'fields': (
                'pending_applications_count',
                'hold_applications_count',
                'canceled_applications_count',
                'completed_applications_count',
                'total_applications_count',
            )
        }),
        (_('Money sum'), {
            'fields': (
                'pending_money_sum',
                'hold_money_sum',
                'canceled_money_sum',
                'completed_money_sum',
                'total_money_sum',
            )
        }),
    )
    always_readonly_fields = (
        'pending_applications_count',
        'hold_applications_count',
        'canceled_applications_count',
        'completed_applications_count',
        'total_applications_count',
        'pending_money_sum',
        'hold_money_sum',
        'canceled_money_sum',
        'completed_money_sum',
        'total_money_sum',
    )

    def get_readonly_fields(self, request, obj=None):
        """
        All money related fields cannot be changed after first exchange operation requested.
        goal and shares can be increased proportionally.
        total valuation and price cannot be changed

        Shares can be specified before start, or after

        """
        if obj is None or not obj.is_active:
            return self.always_readonly_fields
        return {
            'security',
            'round',
            'valuation',
            'price',
            'date_start',
            *self.always_readonly_fields,
        }

    def get_queryset(self, request):
        return super().get_queryset(request).with_application_statistics().with_money_statistics()

    def pending_applications_count(self, obj):
        return obj.pending_applications_count
    pending_applications_count.short_description = 'Pending'

    def hold_applications_count(self, obj):
        return obj.hold_applications_count
    hold_applications_count.short_description = 'Hold'

    def canceled_applications_count(self, obj):
        return obj.canceled_applications_count
    canceled_applications_count.short_description = 'Canceled'

    def total_applications_count(self, obj):
        return obj.total_applications_count
    total_applications_count.short_description = 'Total'

    def completed_applications_count(self, obj):
        return obj.completed_applications_count
    completed_applications_count.short_description = 'Completed'

    def pending_money_sum(self, obj):
        return obj.pending_money_sum
    pending_money_sum.short_description = 'Pending'

    def hold_money_sum(self, obj):
        return obj.hold_money_sum
    hold_money_sum.short_description = 'Hold'

    def canceled_money_sum(self, obj):
        return obj.canceled_money_sum
    canceled_money_sum.short_description = 'Canceled'

    def total_money_sum(self, obj):
        return obj.total_money_sum
    total_money_sum.short_description = 'Total'

    def completed_money_sum(self, obj):
        return obj.completed_money_sum
    completed_money_sum.short_description = 'Completed'
