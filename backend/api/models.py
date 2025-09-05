from django.conf import settings
from django.db import models


class BrandGuideline(models.Model):
    """Stores brand guidelines and content instructions for a user"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="brand_guidelines",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    GUIDELINE_TYPES = [
        ("tone", "Tone of Voice"),
        ("terminology", "Company Terminology"),
        ("style", "Writing Style"),
        ("rules", "Content Rules"),
    ]
    guideline_type = models.CharField(
        max_length=20, choices=GUIDELINE_TYPES, default="tone"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        username = getattr(self.user, "username", str(self.user))
        return f"{self.title} (by {username})"

    class Meta:
        ordering = ["-uploaded_at", "-id"]


class UploadedCampaign(models.Model):
    """Stores a user's uploaded historical email campaign file and parsed metadata"""

    FILE_TYPES = [
        ("csv", "CSV"),
        ("txt", "Text"),
        ("json", "JSON"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_campaigns",
    )
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    raw_content = models.TextField()
    parsed_campaigns = models.JSONField(default=list, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    campaign_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-upload_date", "-id"]


class LinkedInScrape(models.Model):
    """Stores raw scraped LinkedIn page text for a user and URL."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linkedin_scrapes",
    )
    url = models.URLField(max_length=500)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "url"]),
            models.Index(fields=["user", "created_at"]),
        ]