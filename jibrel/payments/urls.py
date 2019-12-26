from jibrel.core.urls import path
from jibrel.payments import views

urlpatterns = [
    *path('assets/', views.AssetsListAPIView.as_view()),
    *path('limits/', views.PaymentLimitsListAPIView.as_view()),

    *path('operations/',  views.OperationViewSet.as_view({'get': 'list'})),
    *path('operations/<pk>/',  views.OperationViewSet.as_view({'get': 'retrieve'})),
    *path('operations/<pk>/upload',  views.UploadOperationConfirmationAPIView.as_view()),

    *path('wire-transfer/', views.BankAccountListAPIView.as_view()),
    *path('wire-transfer/<uuid:bank_account_id>/', views.BankAccountDetailsAPIView.as_view()),
    *path('wire-transfer/<uuid:bank_account_id>/deposit', views.WireTransferDepositAPIView.as_view()),
]
