from jibrel.campaigns.views import OfferingAPIView
from jibrel.core.urls import path
from jibrel.investment.views import (
    CreateInvestmentApplicationAPIView,
    InvestmentApplicationsSummaryAPIView,
    InvestmentApplicationViewSet,
    InvestmentSubscriptionViewSet,
    PersonalAgreementAPIView
)

urlpatterns = [
    *path('offerings/summary', InvestmentApplicationsSummaryAPIView.as_view()),
    *path('offerings/subscriptions', InvestmentSubscriptionViewSet.as_view({'get': 'list'})),
    *path('offerings/<offering_id>', OfferingAPIView.as_view()),
    *path('offerings/<offering_id>/subscribe', InvestmentSubscriptionViewSet.as_view({
        'get': 'retrieve',
        'post': 'create'
    })),
    *path('offerings/<offering_id>/application', CreateInvestmentApplicationAPIView.as_view()),
    *path('offerings/<offering_id>/agreement', PersonalAgreementAPIView.as_view()),
    *path('applications', InvestmentApplicationViewSet.as_view({'get': 'list'})),
    *path('applications/<application_id>', InvestmentApplicationViewSet.as_view({'get': 'retrieve'})),
    *path(
        'applications/<application_id>/finish-signing', InvestmentApplicationViewSet.as_view({
            'post': 'finish_signing'
         })
    ),
    *path(
        'applications/<application_id>/deposit/card', InvestmentApplicationViewSet.as_view({
            'post': 'deposit_card'
        }),
    ),
]
