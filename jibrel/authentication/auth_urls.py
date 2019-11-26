from django.urls import path

from jibrel.authentication import views

urlpatterns = [
    path('registration', views.RegisterAPIView.as_view(), name='register'),
    path('registration/email-verify', views.VerifyEmailAPIView.as_view(), name='verify-password'),
    path(
        'registration/confirmation-email-resend',
        views.ConfirmationEmailResendAPIView.as_view(),
        name='resend-confirmation-email'
    ),
    path('login', views.LoginAPIView.as_view(), name='login'),
    path('logout', views.LogoutAPIView.as_view(), name='logout'),
    path('password/change', views.ChangePasswordAPIView.as_view(), name='change-password'),
    path('password/reset', views.RequestResetPasswordAPIView.as_view(), name='request-reset-password'),
    path('password/reset/activate', views.ActivateResetPasswordAPIView.as_view(), name='activate-reset-password'),
    path('password/reset/complete', views.CompleteResetPasswordAPIView.as_view(), name='complete-reset-password'),
]
