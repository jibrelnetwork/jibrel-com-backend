from jibrel.core.urls import path
from jibrel.investment.views import (
    InvestmentApplicationAPIView,
    InvestmentApplicationsListAPIView,
    InvestmentApplicationsSummaryAPIView,
    PersonalAgreementAPIView
)

urlpatterns = [
    *path('offerings', InvestmentApplicationsListAPIView.as_view()),
    *path('offerings/summary', InvestmentApplicationsSummaryAPIView.as_view()),
    *path('offerings/<offering_id>/application', InvestmentApplicationAPIView.as_view()),
    *path('offerings/<offering_id>/agreement', PersonalAgreementAPIView.as_view()),

]
