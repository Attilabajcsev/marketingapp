from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from .models import VectorizedChunk
from .utils import text_to_vector, sentence_split, rank_by_similarity
from django.conf import settings
import requests
from api.models import BrandGuideline
from .prompt_template import build_generation_messages


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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request: Request) -> Response:
    """
    Minimal chat endpoint. Body: { prompt }
    Uses OpenAI if OPENAI_API_KEY present; otherwise returns an echo.
    """
    data = request.data or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return Response({"error": "Missing prompt"}, status=400)

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if api_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 64,
                },
                timeout=15,
            )
            if resp.ok:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return Response({"reply": text})
            else:
                return Response({"reply": f"LLM error, echoing: {prompt}", "error": resp.text})
        except Exception as e:
            return Response({"reply": f"LLM error, echoing: {prompt}", "error": str(e)})

    return Response({"reply": f"Echo: {prompt}"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate(request: Request) -> Response:
    """
    Enriched generation endpoint using prompt template with:
    - ALL brand guidelines (no RAG)
    - RAG (vector) search ONLY over uploaded campaigns for similar examples
    Body: { "prompt": "...", "top_k": 5 }
    """
    data = request.data or {}
    prompt = (data.get("prompt") or "").strip()
    top_k = int(data.get("top_k") or 5)
    if not prompt:
        return Response({"error": "Missing prompt"}, status=400)

    # Load all brand guidelines for the user and categorize
    qs = BrandGuideline.objects.filter(user=request.user)
    tone = [bg.content for bg in qs.filter(guideline_type="tone")]
    terminology = [bg.content for bg in qs.filter(guideline_type="terminology")]
    style = [bg.content for bg in qs.filter(guideline_type="style")]
    rules = [bg.content for bg in qs.filter(guideline_type="rules")]

    # RAG over uploaded campaigns only
    # Filter vector chunks to uploads
    chunks = list(
        VectorizedChunk.objects.filter(user=request.user, source_type="upload").values(
            "id", "vector", "text", "source_id"
        )
    )
    similar_texts: list[str] = []
    similar_examples: list[dict] = []
    if chunks:
        vectors = [(c["id"], c["vector"]) for c in chunks]
        texts = [c["text"] for c in chunks]
        idxs = rank_by_similarity(prompt, vectors, texts, top_k=top_k)
        id_to_chunk = {c["id"]: c for c in chunks}
        for idx in idxs:
            ch = id_to_chunk.get(idx)
            if ch:
                similar_texts.append(ch["text"])
                similar_examples.append({
                    "chunk_id": ch["id"],
                    "upload_id": ch["source_id"],
                    "text": ch["text"],
                })

    messages = build_generation_messages(
        user_request=prompt,
        tone_guidelines=tone,
        terminology_guidelines=terminology,
        style_guidelines=style,
        content_rules=rules,
        similar_campaigns=similar_texts,
    )

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if api_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return Response({"reply": text, "similar_examples": similar_examples})
            else:
                return Response({"reply": f"LLM error, echoing: {prompt}", "error": resp.text, "similar_examples": similar_examples})
        except Exception as e:
            return Response({"reply": f"LLM error, echoing: {prompt}", "error": str(e), "similar_examples": similar_examples})

    # Fallback echo uses the constructed template context minimally
    synthetic = "\n\n".join([
        "[Tone] " + " | ".join(tone) if tone else "",
        "[Terminology] " + " | ".join(terminology) if terminology else "",
        "[Style] " + " | ".join(style) if style else "",
        "[Rules] " + " | ".join(rules) if rules else "",
        "[Similar] " + " | ".join(similar_texts) if similar_texts else "",
        "[Request] " + prompt,
    ])
    return Response({"reply": synthetic.strip(), "similar_examples": similar_examples})


