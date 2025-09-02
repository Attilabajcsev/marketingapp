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
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        username = getattr(self.user, "username", str(self.user))
        return f"{self.title} (by {username})"

    class Meta:
        ordering = ["-uploaded_at", "-id"]

