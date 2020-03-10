from django.conf import settings
from django.contrib import (
    admin,
    messages
)
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions

from django_banking.admin.base import DisplayUserMixin
from django_banking.admin.helpers import (
    force_link_display,
    get_link_tag
)
from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation
)
from jibrel.investment.admin.filters import ApplicationTypeListFilter
from jibrel.investment.admin.forms import (
    AddPaymentForm,
    PersonalAgreementForm
)
from jibrel.investment.enum import InvestmentApplicationPaymentStatus
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement,
    SubscriptionAgreementTemplate
)


class DisplayOfferingMixin:
    @force_link_display()
    def offering_link(self, obj):
        rel = obj.offering
        return reverse(f'admin:{rel._meta.app_label}_{rel._meta.model_name}_change', kwargs={
            'object_id': str(rel.pk)
        }), rel

    offering_link.short_description = 'offering'


@admin.register(InvestmentApplication)
class InvestmentApplicationModelAdmin(DisplayUserMixin, DisplayOfferingMixin, DjangoObjectActions, admin.ModelAdmin):
    search_fields = (
        'user__pk',
        'user__email',
        'deposit_reference_code',
        'offering__security__company__slug',
    )
    list_filter = (
        'status',
        ApplicationTypeListFilter
    )
    list_display = (
        'user',
        'offering',
        'payment_status',
        'status',
        'amount',
        'created_at',
    )
    readonly_fields = (
        'uuid',
        'offering_link',
        'user_link',
        'deposit',
        'deposit_reference_code',
        'status',
        'is_agreed_risks',
        'is_agreed_subscription',
        'created_at',
        'payment_status',
        'deposit_link',
        'refund_link',
    )
    fieldsets_add_payment = (
        (None, {
            'fields': (
                'swift_code',
                'bank_name',
                'holder_name',
                'iban_number',
                'amount',
            )
        }),
    )

    def get_queryset(self, request):
        return (
            super(InvestmentApplicationModelAdmin, self)
                .get_queryset(request).with_payment_status()
                .with_enqueued_to_cancel()
                .with_enqueued_to_refund()
        )

    def add_payment(self, request, obj):
        if obj.deposit is not None:
            back_url = reverse(
                f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
                kwargs={'object_id': obj.pk}
            )
            self.message_user(request, 'Already paid', messages.ERROR)
            return HttpResponseRedirect(back_url)
        return self.changeform_view(request, object_id=str(obj.pk))

    def refund(self, request, obj):
        meta = DepositWireTransferOperation._meta
        url = reverse(
            f'admin:{meta.app_label}_{meta.model_name}_actions',
            kwargs={
                'pk': obj.deposit.pk,
                'tool': 'refund'
            }
        )
        return HttpResponseRedirect(url)

    def _is_add_payment_form(self, request, obj):
        return obj and request.path == reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_actions', kwargs={
            'pk': obj.pk,
            'tool': 'add_payment'
        })

    def get_fieldsets(self, request, obj=None):
        if self._is_add_payment_form(request, obj):
            return self.fieldsets_add_payment
        return (
            (None, {
                'fields': (
                    'uuid',
                    'user_link',
                    'offering_link',
                    'amount',
                    'status',
                )
            }),
            ('Deposit', {
                'fields': (
                    'payment_status',
                    'deposit_reference_code',
                    'deposit_link',
                    'refund_link',
                )
            }),
            ('Agreements', {
                'fields': (
                    'is_agreed_risks',
                    'is_agreed_subscription',
                )
            }),
            (_('Important dates'), {
                'fields': (
                    'created_at',
                )
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        if self._is_add_payment_form(request, obj):
            return []
        fields = super(InvestmentApplicationModelAdmin, self).get_readonly_fields(request, obj)
        if obj and obj.is_paid:
            fields = (*fields, 'amount')
        return fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        defaults = {}
        if self._is_add_payment_form(request, obj):
            defaults['form'] = AddPaymentForm
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    change_actions = ('add_payment', 'refund')

    def get_change_actions(self, request, object_id, form_url):
        obj = self.get_queryset(request).filter(pk=object_id).first()
        if obj and obj.payment_status == InvestmentApplicationPaymentStatus.NOT_PAID:
            return ('add_payment',)
        if obj and obj.payment_status == InvestmentApplicationPaymentStatus.PAID:
            return ('refund',)
        return super(InvestmentApplicationModelAdmin, self).get_change_actions(request, object_id, form_url)

    def has_add_permission(self, request):
        """
        Disabled temporary
        """
        return False

    def has_delete_permission(self, request, obj=None):
        return settings.ALLOW_INVESTMENT_APPLICATION_DELETION or (
            obj and not obj.deposit_id
        )

    PAYMENT_STATUS_CHOICES = {
        InvestmentApplicationPaymentStatus.NOT_PAID: 'Not paid',
        InvestmentApplicationPaymentStatus.PAID: 'Paid',
        InvestmentApplicationPaymentStatus.REFUND: 'Refund',
    }

    def payment_status(self, obj):
        if obj is not None:
            return self.PAYMENT_STATUS_CHOICES.get(obj.payment_status, None)

    def save_related(self, request, form, formsets, change):
        pass

    @force_link_display()
    def deposit_link(self, obj):
        # TODO operation class should be defined dynamically
        return reverse(
            f'admin:wire_transfer_depositwiretransferoperation_change',
            kwargs={'object_id': obj.deposit.pk}
        ), obj.deposit.pk

    deposit_link.short_description = 'deposit'

    @force_link_display()
    def refund_link(self, obj):
        # TODO operation class should be defined dynamically
        refund = obj.deposit.refund
        return reverse(
            f'admin:wire_transfer_refundwiretransferoperation_change',
            kwargs={'object_id': refund.pk}
        ), refund.pk

    refund_link.short_description = 'refund'


@admin.register(PersonalAgreement)
class PersonalAgreementModelAdmin(DisplayOfferingMixin, DisplayUserMixin, admin.ModelAdmin):
    form = PersonalAgreementForm
    list_filter = (
        'offering',
    )
    list_display = (
        'user',
        'offering',
        'is_agreed',
    )
    search_fields = (
        'user_id',
        'user__email'
    )

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {
                'fields': (
                    'user_link' if obj else 'user',
                    'offering_link' if obj else 'offering',
                    'file',
                    'is_agreed'
                )
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []
        return [
            'user_link',
            'offering_link',
        ]

    def has_delete_permission(self, request, obj=None):
        """
        make sure we have protect from deletion all agreed papers
        """
        if obj:
            return not obj.is_agreed
        return False


@admin.register(SubscriptionAgreementTemplate)
class SubscriptionAgreementTemplateModelAdmin(admin.ModelAdmin):
    pass
