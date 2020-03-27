from decimal import Decimal

from django import forms
from django.contrib import (
    admin,
    messages
)
from django.contrib.admin import helpers
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions

from django_banking import settings

from ..models.accounts.exceptions import AccountBalanceException
from ..models.transactions.enum import OperationStatus
from ..models.transactions.exceptions import OperationBalanceException
from .filters import AssetListFilter
from .helpers import force_link_display


class DisplayUserMixin:
    @staticmethod
    def _get_user(obj):
        return obj.user

    @force_link_display()
    def user_link(self, obj):
        # please not this it is not the same as django.conf.settings
        user = self._get_user(obj)
        return reverse(f'admin:{settings.USER_MODEL.replace(".", "_").lower()}_change', kwargs={
            'object_id': str(user.pk)
        }), str(user.pk)

    user_link.short_description = 'user'


class BaseDepositWithdrawalOperationModelAdmin(DisplayUserMixin, admin.ModelAdmin):
    empty_value_display = '-'

    ordering = ('-created_at',)

    list_display = (
        'uuid',
        'status',
        'user',
        'asset',
        'amount',
        'fee',
        'total_amount',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'uuid',
        'transactions__account__useraccount__user__uuid',
        'transactions__account__useraccount__user__email',
    )

    list_filter = (
        'status',
        AssetListFilter
    )

    def get_queryset(self, request):
        return (
            super(BaseDepositWithdrawalOperationModelAdmin, self).get_queryset(request)
                .with_asset()
                .with_fee()
                .with_amount()
               .with_total_amount()
        )

    def amount(self, obj):
        if isinstance(obj.amount, Decimal):
            return '{:.2f}'.format(obj.amount)
        return obj.amount

    def total_amount(self, obj):
        return obj.total_amount

    def fee(self, obj):
        return obj.fee

    def asset(self, obj):
        return obj.asset

    def user(self, obj):
        return obj.user and obj.user.uuid

    def tx_hash(self, obj):
        return obj.metadata.get('tx_hash')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def after_commit_hook(self, request, obj):
        pass

    def after_cancel_hook(self, request, obj):
        pass


class ActionRequiredDepositWithdrawalOperationModelAdmin(DjangoObjectActions, BaseDepositWithdrawalOperationModelAdmin):
    change_actions = ('commit', 'cancel', 'refund',)

    def get_change_actions(self, request, object_id, form_url):
        all_available_actions = set(super().get_change_actions(request, object_id, form_url))
        allowed_actions = set(ActionRequiredDepositWithdrawalOperationModelAdmin.change_actions)
        other_actions = all_available_actions - allowed_actions
        obj = self.get_object(request, object_id)
        if obj and obj.status == OperationStatus.COMMITTED:
            allowed_actions = {'refund'}
        elif obj and obj.status in (OperationStatus.NEW, OperationStatus.HOLD):
            allowed_actions = {'commit', 'cancel'}
        return sorted(all_available_actions & allowed_actions | other_actions)

    def commit(self, request, obj):
        if obj.is_committed:
            self.message_user(request, 'Confirmed already')
            return
        try:
            obj.commit()
            self.after_commit_hook(request, obj)
            self.message_user(request, 'Operation confirmed')
        except AccountBalanceException:
            self.message_user(request, f'Transition restricted. {AccountBalanceException.reason}', level=messages.ERROR)
        except (OperationBalanceException, AssertionError):
            self.message_user(request, 'Transition restricted.', level=messages.ERROR)

    def cancel(self, request, obj):
        if obj.is_cancelled:
            self.message_user(request, 'Rejected already')
            return
        obj.cancel()
        self.after_cancel_hook(request, obj)
        self.message_user(request, 'Operation rejected')

    def refund(self, request, obj):
        self.message_user(request, 'Not supported yet', messages.ERROR)

    commit.label = 'COMMIT'
    cancel.label = 'CANCEL'

    def render_custom_form(self, request, obj, form, instance, template,
                           custom_context=None, success_message='Success!'):
        object_id = obj.pk
        model = self.model
        opts = model._meta
        kw = {'instance': instance} if issubclass(form, forms.ModelForm) else {}
        if request.method == 'POST':
            form = form(request.POST, **kw)
            is_valid = form.is_valid()
            if is_valid:
                form.save()
                self.message_user(request, success_message, messages.SUCCESS)
                return HttpResponseRedirect(reverse(
                    f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
                    kwargs={'object_id': obj.pk}
                ))
        else:
            form = form(**kw)
        formsets = [(None, {'fields': form.base_fields})]
        adminForm = helpers.AdminForm(form, formsets, {}, [], model_admin=self)

        media = self.media + adminForm.media
        title = _('Change %s')
        context = {
            **self.admin_site.each_context(request),
            'opts': opts,
            'title': title % opts.verbose_name,
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': False,
            'media': media,
            'add': False,
            'change': True,
            'save_as': False,
            'save_on_top': False,
            'has_view_permission': False,
            'has_add_permission': False,
            'has_change_permission': True,
            'has_delete_permission': False,
            'has_editable_inline_admin_formsets': False,
            'has_file_field': False,
            'errors': helpers.AdminErrorList(form, ()),
            'preserved_filters': []
        }
        context.update(custom_context or {})
        return TemplateResponse(request, template, context)
