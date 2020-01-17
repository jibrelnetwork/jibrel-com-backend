from django.urls import path

from jibrel.campaigns import views

urlpatterns = [
    path('company/<company>/offerings', views.OfferingsAPIView.as_view()),
    path('company/<company>/offerings/active', views.ActiveOfferingAPIView.as_view())
]
