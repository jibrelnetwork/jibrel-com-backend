# from jibrel.core.urls import path
# from jibrel.payments import views
#
# urlpatterns = [
#     *path('limits/', views.PaymentLimitsListAPIView.as_view()),
#
#     *path('cards/', views.CardListAPIView.as_view()),
#     *path('cards/<card_id>/deposit', views.CardDepositAPIView.as_view()),
#     *path('cards/<card_id>/charge', views.CardChargeAPIView.as_view()),
#
#     *path('bank-account/', views.BankAccountListAPIView.as_view()),
#     *path('bank-account/<uuid:bank_account_id>/', views.BankAccountDetailsAPIView.as_view()),
#     *path('bank-account/<uuid:bank_account_id>/deposit', views.BankAccountDepositAPIView.as_view()),
#     *path('bank-account/<uuid:bank_account_id>/withdrawal', views.BankAccountWithdrawalAPIView.as_view()),
#     *path(
#         'bank-account/<uuid:bank_account_id>/withdrawal/calculate',
#         views.BankAccountWithdrawalCalculateAPIView.as_view()
#     ),
#
#     *path('cryptocurrency/', views.CryptoAccountListAPIView.as_view()),
#     *path('cryptocurrency/<uuid:pk>/', views.CryptoAccountDetailsAPIView.as_view()),
#     *path('cryptocurrency/<uuid:pk>/withdrawal/', views.CryptoAccountWithdrawalAPIView.as_view()),
#     *path('cryptocurrency/withdrawal/<uuid:asset_id>/calculate', views.CryptoWithdrawalCalculateAPIView.as_view()),
#     *path('cryptocurrency/deposit/<uuid:asset_id>/', views.CryptoAccountDepositAPIView.as_view()),
#
#     # Deprecated
#     *path('bank_account/', views.BankAccountListAPIView.as_view()),
#     *path('bank_account/<uuid:bank_account_id>/', views.BankAccountDetailsAPIView.as_view()),
#     *path('bank_account/<uuid:bank_account_id>/deposit', views.BankAccountDepositAPIView.as_view()),
#     *path('bank_account/<uuid:bank_account_id>/withdrawal', views.BankAccountWithdrawalAPIView.as_view()),
#     # /Deprecated
# ]
