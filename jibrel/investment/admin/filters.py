from django.contrib import admin


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
