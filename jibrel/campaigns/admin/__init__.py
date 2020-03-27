from django.contrib import (
    admin,
    messages
)
from django.contrib.admin.utils import flatten_fieldsets
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions

from django_banking.admin.helpers import force_link_display
from jibrel.campaigns.admin.forms import (
    OfferingForm,
    SecurityForm
)
from jibrel.campaigns.models import (
    Company,
    Offering,
    Security
)
from jibrel.core.xls import get_xlsx
from jibrel.investment.enum import InvestmentApplicationStatus
from jibrel.investment.models import InvestmentApplication


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

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {
                'fields': (
                    'company_link' if obj else 'company',
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
        all_fields = set(flatten_fieldsets(self.get_fieldsets(request, obj)))

        # TODO
        # https://code.djangoproject.com/ticket/29682
        return all_fields - {
            'asset__symbol'
        }

    @force_link_display()
    def company_link(self, obj):
        rel = obj.company
        return reverse(f'admin:{rel._meta.app_label}_{rel._meta.model_name}_change', kwargs={
            'object_id': str(rel.pk)
        }), rel

    company_link.short_description = 'company'


@admin.register(Offering)
class OfferingAdmin(DjangoObjectActions, admin.ModelAdmin):
    save_as_continue = False
    save_as = False
    form = OfferingForm
    ordering = ('-created_at',)
    change_actions = ('waitlist',)

    readonly_fields = (
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
        'security_link'
    )

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {
                'fields': (
                    'security_link' if obj else 'security',
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

    def get_readonly_fields(self, request, obj=None):
        """
        All money related fields cannot be changed after first exchange operation requested.
        goal and shares can be increased proportionally.
        total valuation and price cannot be changed

        Shares can be specified before start, or after

        """
        if obj is None or not obj.is_active:
            return self.readonly_fields
        return {
            'security',
            'round',
            *self.readonly_fields,
        }

    def get_queryset(self, request):
        return super().get_queryset(request).with_application_statistics().with_money_statistics()

    @force_link_display()
    def pending_applications_count(self, obj):
        model = InvestmentApplication
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        return f'{url}?offering={obj.pk}&status__exact={InvestmentApplicationStatus.PENDING}', \
               obj.pending_applications_count
    pending_applications_count.short_description = 'Pending'

    @force_link_display()
    def hold_applications_count(self, obj):
        model = InvestmentApplication
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        return f'{url}?offering={obj.pk}&status__exact={InvestmentApplicationStatus.HOLD}', \
               obj.hold_applications_count
    hold_applications_count.short_description = 'Hold'

    @force_link_display()
    def canceled_applications_count(self, obj):
        model = InvestmentApplication
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        return f'{url}?offering={obj.pk}&status__exact={InvestmentApplicationStatus.CANCELED}', \
               obj.canceled_applications_count
    canceled_applications_count.short_description = 'Canceled'

    @force_link_display()
    def total_applications_count(self, obj):
        model = InvestmentApplication
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        return f'{url}?offering={obj.pk}', obj.total_applications_count
    total_applications_count.short_description = 'Total'

    @force_link_display()
    def completed_applications_count(self, obj):
        model = InvestmentApplication
        url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
        return f'{url}?offering={obj.pk}&status__exact={InvestmentApplicationStatus.COMPLETED}', \
               obj.completed_applications_count
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

    @force_link_display()
    def security_link(self, obj):
        rel = obj.security
        return reverse(f'admin:{rel._meta.app_label}_{rel._meta.model_name}_change', kwargs={
            'object_id': str(rel.pk)
        }), rel

    security_link.short_description = 'security'

    def waitlist(self, request, obj):
        subs = obj.subscribes.with_full_name()
        if not subs.exists():
            self.message_user(request, 'There is not any users at waitlist', level=messages.INFO)
            return

        now = timezone.now()
        cols = [
            (u'E-mail', 40, 'email'),
            (u'Full name', 25, 'full_name'),
            (u'Amount', 25, 'amount', 'decimal'),
        ]
        header = "Grabbed at: {}\n".format(
            now.strftime('%d/%m/%Y')
        )
        return get_xlsx(cols, subs, filename='datasheet.{}'.format(now.timestamp()), header=header)
