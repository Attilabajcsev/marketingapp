from django.urls import path
from . import views
from .views import brand_guidelines_list, brand_guidelines_create
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
    # Brand guidelines
    path("brand-guidelines/", brand_guidelines_list, name="brand_guidelines_list"),
    path("brand-guidelines", brand_guidelines_list),
    path(
        "brand-guidelines/create/",
        brand_guidelines_create,
        name="brand_guidelines_create",
    ),
    path("brand-guidelines/create", brand_guidelines_create),
]
