from jibrel.core.urls import path
from jibrel.payments import views

urlpatterns = [
    *path('limits/', views.PaymentLimitsListAPIView.as_view()),

    *path('wire_transfer-transfer/', views.BankAccountListAPIView.as_view()),
    *path('wire_transfer-transfer/<uuid:bank_account_id>/', views.BankAccountDetailsAPIView.as_view()),
    *path('wire_transfer-transfer/<uuid:bank_account_id>/deposit', views.BankAccountDepositAPIView.as_view()),
]
