from django.urls import path

from jibrel.kyc import views

urlpatterns = [
    path('document', views.UploadDocumentAPIView.as_view()),
    path('phone', views.PhoneAPIView.as_view()),
    path('phone/resend-sms', views.ResendSMSAPIView.as_view()),
    path('phone/call-me', views.CallPhoneAPIView.as_view()),
    path('phone/verify', views.VerifyPhoneAPIView.as_view()),
    path('individual', views.IndividualKYCSubmissionAPIView.as_view()),
    path('individual/validate', views.IndividualKYCValidateAPIView.as_view()),
    path('organization', views.OrganisationalKYCSubmissionAPIView.as_view()),
    path('organization/validate', views.OrganisationalKYCValidateAPIView.as_view()),
]
