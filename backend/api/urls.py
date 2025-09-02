from django.urls import path
from . import views
from .views import email_campaigns_list, email_campaigns_create
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    # Authentication
    path("register/", views.create_user, name="register"),
    path("oauth-google/", views.oauth_google, name="oauth-google"),
    path("login/", TokenObtainPairView.as_view(), name="get_token"),
    path("token/verify/", TokenVerifyView.as_view(), name="verify_token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh_token"),
    path("user/profile/", views.user_profile, name="user_profile"),
    # Email campaigns
    path("email-campaigns/", email_campaigns_list, name="email_campaigns_list"),
    path(
        "email-campaigns/create/",
        email_campaigns_create,
        name="email_campaigns_create",
    ),
]
