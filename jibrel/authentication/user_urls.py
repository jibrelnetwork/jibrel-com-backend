from django.urls import path

from jibrel.authentication import views

urlpatterns = [
    path('profile', views.UserProfileAPIView.as_view(), name='profile'),
    path('profile/language', views.SetLanguageAPIView.as_view(), name='profile-set-language'),
    path('limits', views.LimitsAPIView.as_view(), name='limits'),
]
