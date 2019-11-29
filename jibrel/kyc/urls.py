from django.urls import path

from jibrel.kyc import views

urlpatterns = [
    path('document', views.UploadDocumentAPIView.as_view()),
    path('phone', views.PhoneAPIView.as_view()),
    path('phone/resend-sms', views.ResendSMSAPIView.as_view()),
    path('phone/call-me', views.CallPhoneAPIView.as_view()),
    path('phone/verify', views.VerifyPhoneAPIView.as_view()),
    path('personal', views.PersonalKYCSubmissionAPIView.as_view()),
    path('organization', views.BusinessKYCSubmissionAPIView.as_view()),
    path('submissions', views.KYCSubmissionList.as_view()),
    path('added-docs', views.KYCAddedDocumentsAPIView.as_view()),
    path('subscribed-countries', views.SubscribedCountriesAPIView.as_view()),
]
