from django.conf import settings
from django.db import models


class VectorizedChunk(models.Model):
    """Stores a vectorized text chunk associated with a user and source."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vector_chunks",
    )
    source_type = models.CharField(max_length=32)  # 'guideline' | 'upload'
    source_id = models.IntegerField()
    text = models.TextField()
    # Store vector as JSON array of floats for simplicity; can switch to pgvector later
    vector = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "source_type", "source_id"]),
            models.Index(fields=["user", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]


