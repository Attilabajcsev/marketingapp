from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from .models import VectorizedChunk
from .utils import text_to_vector, sentence_split, rank_by_similarity


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ingest_text(request: Request) -> Response:
    """
    Ingest text content as chunks -> vectors. Body JSON:
    { "source_type": "guideline"|"upload", "source_id": 123, "text": "..." }
    """
    data = request.data or {}
    source_type = data.get("source_type")
    source_id = data.get("source_id")
    text = data.get("text")
    if source_type not in {"guideline", "upload"} or not isinstance(source_id, int) or not text:
        return Response({"error": "Invalid payload"}, status=400)

    chunks = sentence_split(text)
    created = []
    for chunk in chunks:
        vec = text_to_vector(chunk)
        obj = VectorizedChunk.objects.create(
            user=request.user,
            source_type=source_type,
            source_id=source_id,
            text=chunk,
            vector=vec,
        )
        created.append(obj.id)
    return Response({"created_ids": created}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def search(request: Request) -> Response:
    """
    Simple vector search. Body JSON: { "query": "...", "top_k": 5 }
    Returns: list of { id, text, source_type, source_id, score }
    """
    data = request.data or {}
    query = data.get("query")
    top_k = int(data.get("top_k") or 5)
    if not query:
        return Response({"error": "Missing query"}, status=400)

    chunks = list(VectorizedChunk.objects.filter(user=request.user).values("id", "vector", "text", "source_type", "source_id"))
    if not chunks:
        return Response({"results": []})

    vectors = [(c["id"], c["vector"]) for c in chunks]
    idxs = rank_by_similarity(query, vectors, [c["text"] for c in chunks], top_k=top_k)
    id_set = set(idxs)
    # Keep original ordering by similarity
    ordered = [c for c in chunks if c["id"] in id_set]
    return Response({"results": ordered})


