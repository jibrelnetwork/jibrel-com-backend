from jibrel.core.urls import path
from jibrel.investment.views import (
    CreateInvestmentApplicationAPIView,
    InvestmentApplicationsSummaryAPIView,
    InvestmentApplicationViewSet,
    InvestmentSubscriptionAPIView,
    PersonalAgreementAPIView
)

urlpatterns = [
    *path('offerings', InvestmentApplicationViewSet.as_view({'get': 'list'})),  # FIXME deprecated
    *path('offerings/summary', InvestmentApplicationsSummaryAPIView.as_view()),
    *path('offerings/<offering_id>/subscribe', InvestmentSubscriptionAPIView.as_view()),
    *path('offerings/<offering_id>/application', CreateInvestmentApplicationAPIView.as_view()),
    *path('offerings/<offering_id>/agreement', PersonalAgreementAPIView.as_view()),
    *path('applications', InvestmentApplicationViewSet.as_view({'get': 'list'})),
    *path('applications/<application_id>', InvestmentApplicationViewSet.as_view({'get': 'retrieve'})),
    *path(
        'applications/<application_id>/finish-signing', InvestmentApplicationViewSet.as_view({'post': 'finish_signing'})
    ),
]
