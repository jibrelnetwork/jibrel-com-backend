from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets

from jibrel.notifications.models import ExternalServiceCallLog
from jibrel_admin.common import display_boolean


@admin.register(ExternalServiceCallLog)
class ExternalServiceCallLogAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'action_type',
        'created_at',
        'success'
    )
    fieldsets = (
        (None, {
            'fields': (
                'action_type',
                'initiator_type',
                'initiator',
                'initiator_ip',
            )
        }),
        (None, {
            'fields': (
                'kwargs',
                'request_data',
            )
        }),
        (None, {
            'fields': (
                'response_data',
            )
        }),
        (None, {
            'fields': (
                'created_at',
                'processed_at',
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        all_fields = set(flatten_fieldsets(self.fieldsets))
        return all_fields

    @display_boolean
    def success(self, obj):
        return obj.success

    success.short_description = 'Success'
