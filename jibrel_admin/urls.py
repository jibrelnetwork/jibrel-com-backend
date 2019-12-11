from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

from .views import healthcheck

admin.site.site_title = 'Jibrel Admin'
admin.site.site_header = 'Jibrel Admin'
admin.site.index_title = 'Jibrel Admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin_tools/', include('admin_tools.urls')),
    path('nested_admin/', include('nested_admin.urls')),
    path('healthcheck', healthcheck, name='healthcheck'),
    path('', RedirectView.as_view(url=reverse_lazy('admin:index'))),
]
