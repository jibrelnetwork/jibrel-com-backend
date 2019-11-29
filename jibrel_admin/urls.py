from django.contrib import admin
from django.urls import include, path

from .views import healthcheck

admin.site.site_title = 'CoinMENA Admin'
admin.site.site_header = 'CoinMENA Admin'
admin.site.index_title = 'CoinMENA Admin'

urlpatterns = [
    path('', admin.site.urls),
    path('admin_tools/', include('admin_tools.urls')),
    path('nested_admin/', include('nested_admin.urls')),
    path('select2/', include('django_select2.urls')),
    path('healthcheck', healthcheck, name='healthcheck')
]
