from jibrel.core.urls import path
from jibrel.investment.views import (
    InvestmentApplicationAPIView,
    InvestmentApplicationsListAPIView
)

urlpatterns = [
    *path('offerings', InvestmentApplicationsListAPIView.as_view()),
    *path('offerings/<offering_id>/application', InvestmentApplicationAPIView.as_view())
]
