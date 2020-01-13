
from rest_framework.routers import DefaultRouter

from jibrel.wallets import views

router = DefaultRouter()
router.register(r'wallets', views.WalletViewSet, basename='wallet')

urlpatterns = router.urls
