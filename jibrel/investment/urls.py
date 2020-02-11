from jibrel.campaigns.views import OfferingAPIView
from jibrel.core.urls import path
from jibrel.investment.views import (
    InvestmentApplicationAPIView,
    InvestmentApplicationsListAPIView,
    InvestmentApplicationsSummaryAPIView,
    InvestmentSubscriptionAPIView,
    PersonalAgreementAPIView
)

urlpatterns = [
    *path('offerings', InvestmentApplicationsListAPIView.as_view()),
    *path('offerings/summary', InvestmentApplicationsSummaryAPIView.as_view()),
    *path('offerings/<offering_id>', OfferingAPIView.as_view()),
    *path('offerings/<offering_id>/subscribe', InvestmentSubscriptionAPIView.as_view()),
    *path('offerings/<offering_id>/application', InvestmentApplicationAPIView.as_view()),
    *path('offerings/<offering_id>/agreement', PersonalAgreementAPIView.as_view()),
]
