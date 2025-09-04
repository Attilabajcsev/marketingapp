from __future__ import annotations

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import BrandGuideline, UploadedCampaign
from vectorstore.models import VectorizedChunk
from vectorstore.utils import text_to_vector, sentence_split


def _delete_vectors(user_id: int, source_type: str, source_id: int) -> None:
    VectorizedChunk.objects.filter(
        user_id=user_id, source_type=source_type, source_id=source_id
    ).delete()


@receiver(post_save, sender=BrandGuideline)
def vectorize_brand_guideline(sender, instance: BrandGuideline, **kwargs) -> None:
    # Delete previous vectors for this guideline, then re-index
    _delete_vectors(instance.user_id, "guideline", instance.id)

    content = instance.content or ""
    title = (instance.title or "").strip()
    text = f"{title}\n{content}" if title else content
    if not text.strip():
        return

    chunks = sentence_split(text)
    objs = []
    for chunk in chunks:
        vec = text_to_vector(chunk)
        objs.append(
            VectorizedChunk(
                user_id=instance.user_id,
                source_type="guideline",
                source_id=instance.id,
                text=chunk,
                vector=vec,
            )
        )
    if objs:
        VectorizedChunk.objects.bulk_create(objs)


@receiver(post_delete, sender=BrandGuideline)
def cleanup_brand_guideline_vectors(sender, instance: BrandGuideline, **kwargs) -> None:
    _delete_vectors(instance.user_id, "guideline", instance.id)


@receiver(post_save, sender=UploadedCampaign)
def vectorize_uploaded_campaign(sender, instance: UploadedCampaign, **kwargs) -> None:
    # Delete previous vectors for this upload, then index parsed campaigns
    _delete_vectors(instance.user_id, "upload", instance.id)

    items = instance.parsed_campaigns or []
    if not isinstance(items, list):
        return

    objs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        body = str(item.get("content") or "").strip()
        if not title and not body:
            continue
        text = f"{title}\n{body}" if title else body
        # Do not over-chunk uploads: index each parsed campaign as a single chunk
        vec = text_to_vector(text)
        objs.append(
            VectorizedChunk(
                user_id=instance.user_id,
                source_type="upload",
                source_id=instance.id,
                text=text,
                vector=vec,
            )
        )
    if objs:
        VectorizedChunk.objects.bulk_create(objs)


@receiver(post_delete, sender=UploadedCampaign)
def cleanup_uploaded_campaign_vectors(sender, instance: UploadedCampaign, **kwargs) -> None:
    _delete_vectors(instance.user_id, "upload", instance.id)


