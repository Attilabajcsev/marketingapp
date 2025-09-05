from django.urls import path
from . import views
from .views import (
    brand_guidelines_list,
    brand_guidelines_create,
    brand_guideline_detail,
    uploaded_campaigns_list,
    upload_campaign_file,
    uploaded_campaign_detail,
    linkedin_scrape,
)
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
    path("brand-guidelines/<int:guideline_id>/", brand_guideline_detail, name="brand_guideline_detail"),
    # Uploaded campaign files
    path("uploaded-campaigns/", uploaded_campaigns_list, name="uploaded_campaigns_list"),
    path("uploaded-campaigns", uploaded_campaigns_list),
    path(
        "uploaded-campaigns/upload/",
        upload_campaign_file,
        name="upload_campaign_file",
    ),
    path("uploaded-campaigns/upload", upload_campaign_file),
    path("uploaded-campaigns/<int:upload_id>/", uploaded_campaign_detail, name="uploaded_campaign_detail"),
    # LinkedIn scraping
    path("linkedin/scrape/", linkedin_scrape, name="linkedin_scrape"),
]
