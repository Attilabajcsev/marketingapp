from django.contrib import admin
from .models import VectorizedChunk


@admin.register(VectorizedChunk)
class VectorizedChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source_type", "source_id", "created_at")
    search_fields = ("text", "user__username", "source_type")
    list_filter = ("source_type", "created_at")

