from jibrel.core.urls import path
from jibrel.investment.views import InvestmentApplicationAPIView

urlpatterns = [
    *path('offerings/<offering_id>/application', InvestmentApplicationAPIView.as_view())
]
