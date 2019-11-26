from constance.admin import Config, ConstanceAdmin
from django.contrib import admin


class FixedConstanceAdmin(ConstanceAdmin):
    # admin_tools capability
    # to avoid /admin/constance/ error 500
    # https://github.com/jazzband/django-constance/issues/244

    def __init__(self, model, admin_site):
        model._meta.concrete_model = Config
        super().__init__(model, admin_site)


admin.site.unregister([Config])
admin.site.register([Config], FixedConstanceAdmin)
