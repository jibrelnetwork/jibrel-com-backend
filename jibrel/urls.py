from django.urls import include
from django.views.generic import TemplateView

from jibrel.campaigns.views import CMSOfferingsAPIView
from jibrel.core.swagger import SwaggerJsonSchema
from jibrel.core.urls import path
from jibrel.views import HealthcheckAPIView

v1 = [
    *path('auth/', include('jibrel.authentication.auth_urls')),
    *path('user/', include('jibrel.authentication.user_urls')),
    *path('kyc/', include('jibrel.kyc.urls')),
    *path('payments/', include('jibrel.payments.urls')),
    *path('campaigns/', include('jibrel.campaigns.urls')),
    *path('', include('jibrel.wallets.urls')),
]

urlpatterns = [
    *path('v1/', include(v1)),
    *path('api/doc/', TemplateView.as_view(
            template_name='redoc.html'
        ), name='redoc'),
    *path('api/doc/swagger.json', SwaggerJsonSchema.as_view(), name='swagger-json'),
    *path('healthcheck', HealthcheckAPIView.as_view(), name='healthcheck'),
    *path('cms/company/<company>/offerings', CMSOfferingsAPIView.as_view())
]
