from django.contrib import (
    admin,
    messages
)
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from django_banking.admin.helpers import get_link_tag
from django_banking.contrib.wire_transfer.models import (
    DepositWireTransferOperation,
    UserBankAccount
)
from jibrel.investment.admin.forms import AddPaymentForm, PersonalAgreementForm
from jibrel.investment.enum import InvestmentApplicationPaymentStatus
from jibrel.investment.models import (
    InvestmentApplication,
    PersonalAgreement
)


class ApplicationTypeListFilter(admin.SimpleListFilter):
    title = 'state'
    parameter_name = 'state'

    def lookups(self, request, model_admin):
        return (
            ('enqueued_to_cancel', 'Waiting for cancel'),
            ('enqueued_to_refund', 'Waiting for refund'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val is not None:
            queryset = queryset.filter(
                **{val: True}
            )
        return queryset


@admin.register(InvestmentApplication)
class InvestmentApplicationModelAdmin(DjangoObjectActions, admin.ModelAdmin):
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
    fields = (
        'user',
        'offering',
        'deposit_reference_code',
        'status',
        'is_agreed_risks',
        'is_agreed_subscription',
        'amount',
        'created_at',
        'payment_status',
        'deposit_link',
        'refund_link',
    )
    readonly_fields = (
        'user',
        'offering',
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

    def get_queryset(self, request):
        return (
            super(InvestmentApplicationModelAdmin, self)
                .get_queryset(request).with_payment_status()
                .with_enqueued_to_cancel()
                .with_enqueued_to_refund()
        )

    def add_payment(self, request, obj):
        back_url = reverse(
            f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
            kwargs={'object_id': obj.pk}
        )
        if obj.deposit is not None:
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

    def get_fields(self, request, obj=None):
        if self._is_add_payment_form(request, obj):
            return (
                'swift_code',
                'bank_name',
                'holder_name',
                'iban_number',
                'amount',
            )
        return super(InvestmentApplicationModelAdmin, self).get_fields(request, obj)

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

    @mark_safe
    def deposit_link(self, obj):
        return get_link_tag(reverse(
            f'admin:wire_transfer_depositwiretransferoperation_change',
            kwargs={'object_id': obj.deposit.pk}
        ), obj.deposit.pk)

    @mark_safe
    def refund_link(self, obj):
        return get_link_tag(reverse(
            f'admin:wire_transfer_refundwiretransferoperation_change',
            kwargs={'object_id': obj.refund.pk}
        ), obj.refund.pk)


@admin.register(PersonalAgreement)
class PersonalAgreementModelAdmin(admin.ModelAdmin):
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

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []
        return [
            'user',
            'offering',
        ]

    def has_delete_permission(self, request, obj=None):
        """
        make sure we have protect from deletion all agreed papers
        """
        if obj:
            return not obj.is_agreed
        return False
