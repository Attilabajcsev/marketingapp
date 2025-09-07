from django.contrib import admin
from .models import (
    BrandGuideline,
    UploadedCampaign,
    LinkedInScrape,
    TrustpilotScrape,
    WebsiteScrape,
)


@admin.register(BrandGuideline)
class BrandGuidelineAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "guideline_type", "user", "uploaded_at")
    list_filter = ("guideline_type", "uploaded_at", "user")
    search_fields = ("title", "content", "user__username")


@admin.register(UploadedCampaign)
class UploadedCampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "file_type", "user", "campaign_count", "upload_date")
    list_filter = ("file_type", "upload_date", "user")
    search_fields = ("filename", "user__username")


@admin.register(LinkedInScrape)
class LinkedInScrapeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "url", "created_at")
    search_fields = ("url", "content", "user__username")
    list_filter = ("created_at", "user")


@admin.register(TrustpilotScrape)
class TrustpilotScrapeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "url", "created_at")
    search_fields = ("url", "content", "user__username")
    list_filter = ("created_at", "user")


@admin.register(WebsiteScrape)
class WebsiteScrapeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "url", "created_at")
    search_fields = ("url", "user__username")
    list_filter = ("created_at", "user")
