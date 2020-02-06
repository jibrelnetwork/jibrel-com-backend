from operator import attrgetter

import django.forms
from django.conf import settings
from django.contrib import (
    admin,
    messages
)
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions
from nested_admin import nested

from jibrel.authentication.models import (
    OneTimeToken,
    User
)
from jibrel.core.common.constants import BOOL_TO_STR

from ..signals import password_reset_requested
from .forms import CustomerUserCreationForm
from .inlines import ProfileInline


@admin.register(User)
class CustomerUserModelAdmin(DjangoObjectActions, UserAdmin, nested.NestedModelAdmin):
    add_form_template = 'admin/authentication/user/add_form.html'
    change_form_template = 'admin/authentication/user/change_form.html'
    add_form = CustomerUserCreationForm
    empty_value_display = '-'

    ordering = ('-created_at',)

    list_display = (
        'uuid',
        'email',
        'current_phone',
        'residency_country',
        'full_name',
        'passport_number',
        'kyc_status',
        'is_active',
        'created_at',
        'admin_note'
    )
    search_fields = (
        'uuid',
        'email',
        'admin_note',
        'profile__last_kyc__individual__passport_number',
        'full_name',
        'current_phone',
    )
    fields = None
    readonly_fields = (
        'uuid',
        'email',
        'last_login',
        'created_at',
    )
    actions = []
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'uuid',
                'password',
                'email',
                'admin_note',
                'is_email_confirmed',
                'is_active',
            ),
        }),
        (_('Important dates'), {
             'fields': (
                 'last_login',
                 'created_at',
             ),
        })
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('user_email', 'password1', 'password2',),
        }),
    )
    list_filter = ()
    filter_horizontal = ()

    formfield_overrides = {
        models.BooleanField: {
            'widget': django.forms.widgets.Select(choices=BOOL_TO_STR)
        },
    }

    inlines = [ProfileInline]

    def current_phone(self, user):
        return user.current_phone

    def full_name(self, user):
        return user.full_name

    def kyc_status(self, user):
        return user.profile.get_kyc_status_display()

    def passport_number(self, user):
        return user.profile.last_kyc and user.profile.last_kyc.details.passport_number

    def residency_country(self, user):
        return user.profile.last_kyc and user.profile.last_kyc.details.country

    def send_password_reset_mail(self, request, obj):
        # ip is not displayed here as soon as it is not a client ip
        password_reset_requested.send(sender=User, instance=obj, user_ip_address='')
        messages.add_message(request, messages.INFO, 'Email has been sent')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('profile__last_kyc').with_full_name()
        qs = qs.with_current_phone()
        return qs

    change_actions = ('send_password_reset_mail',)


class OneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'created_at')
    ordering = ('-created_at',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return set(map(attrgetter('name'), self.model._meta.get_fields())) - {
            'id'
        }


if settings.OTT_DEBUG:
    admin.site.register(OneTimeToken, OneTimeTokenAdmin)
