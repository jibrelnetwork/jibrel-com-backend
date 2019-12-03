import django.forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from nested_admin import nested

from jibrel.authentication.models import User
from jibrel.core.common.constants import BOOL_TO_STR
from jibrel_admin.celery import send_password_reset_mail

from .forms import CustomerUserCreationForm
from .inlines import ProfileInline


@admin.register(User)
class CustomerUserModelAdmin(UserAdmin, nested.NestedModelAdmin):
    add_form_template = 'admin/authentication/add_form.html'
    add_form = CustomerUserCreationForm
    empty_value_display = '-'

    ordering = ('-created_at',)

    list_display = (
        'uuid',
        'email',
        'current_phone',
        'residency_country',
        'full_name',
        'personal_id_number',
        'kyc_status',
        'is_blocked',
        'created_at',
        'admin_note',
        'send_password_reset_link',
    )
    search_fields = (
        'uuid',
        'email',
        'admin_note',
        'profile__last_basic_kyc__personal_id_number',
        'full_name',
        'current_phone',
    )
    fields = (
        'uuid',
        'password',
        'email',
        'is_email_confirmed',
        'is_blocked',
        'last_login',
        'created_at',
        'admin_note',
    )
    readonly_fields = (
        'uuid',
        'email',
        'last_login',
        'created_at',
    )
    actions = []
    fieldsets = ()
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

    def personal_id_number(self, user):
        return user.profile.last_basic_kyc and user.profile.last_basic_kyc.personal_id_number

    def residency_country(self, user):
        return user.profile.last_basic_kyc and user.profile.last_basic_kyc.residency

    def send_password_reset_link(self, user):
        url = reverse(
            f'admin:customer_user_password_reset_mail',
            args=(user.pk,)
        )
        return mark_safe(f'<a href={url}>Send email</a>')
    send_password_reset_link.short_description = 'Password reset'

    def send_password_reset_mail_view(self, request, pk):
        user_ip = ''  # TODO get real ip
        send_password_reset_mail(user_ip, pk)
        messages.add_message(request, messages.INFO, 'Email has been sent')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                'password_reset_mail/<pk>',
                self.admin_site.admin_view(self.send_password_reset_mail_view),
                name='customer_user_password_reset_mail'
            )
        ]
        return my_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('profile__last_basic_kyc').with_full_name()
        qs = qs.with_current_phone()
        return qs
