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
# Trustpilot support removed
from api.models import WebsiteScrape
from .prompt_template import build_generation_messages
from api.models import LinkedInScrape


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
    content_type = (data.get("content_type") or "").strip().lower()
    top_k = int(data.get("top_k") or 5)
    if not prompt:
        return Response({"error": "Missing prompt"}, status=400)

    # Load all brand guidelines for the user and categorize
    qs = BrandGuideline.objects.filter(user=request.user)
    tone = [bg.content for bg in qs.filter(guideline_type="tone")]
    terminology = [bg.content for bg in qs.filter(guideline_type="terminology")]
    style = [bg.content for bg in qs.filter(guideline_type="style")]
    rules = [bg.content for bg in qs.filter(guideline_type="rules")]

    # RAG over uploads and websites separately
    uploads_chunks = list(
        VectorizedChunk.objects.filter(user=request.user, source_type="upload").values(
            "id", "vector", "text", "source_id"
        )
    )
    # Prefer the most recent website scrape's chunks to avoid mixing old sites
    latest_ws = WebsiteScrape.objects.filter(user=request.user).order_by("-created_at").first()
    website_chunks_qs = VectorizedChunk.objects.filter(user=request.user, source_type="website")
    if latest_ws:
        website_chunks_qs = website_chunks_qs.filter(source_id=latest_ws.id)
    websites_chunks = list(website_chunks_qs.values("id", "vector", "text", "source_id"))

    rag_uploads: list[str] = []
    rag_uploads_examples: list[dict] = []
    if uploads_chunks:
        u_vectors = [(c["id"], c["vector"]) for c in uploads_chunks]
        u_texts = [c["text"] for c in uploads_chunks]
        u_idxs = rank_by_similarity(prompt, u_vectors, u_texts, top_k=top_k)
        u_map = {c["id"]: c for c in uploads_chunks}
        for idx in u_idxs:
            ch = u_map.get(idx)
            if ch:
                rag_uploads.append(ch["text"])
                rag_uploads_examples.append({
                    "chunk_id": ch["id"],
                    "source_type": "upload",
                    "source_id": ch["source_id"],
                    "text": ch["text"],
                })

    rag_websites: list[str] = []
    rag_websites_examples: list[dict] = []
    if websites_chunks:
        w_vectors = [(c["id"], c["vector"]) for c in websites_chunks]
        w_texts = [c["text"] for c in websites_chunks]
        w_idxs = rank_by_similarity(prompt, w_vectors, w_texts, top_k=top_k)
        w_map = {c["id"]: c for c in websites_chunks}
        for idx in w_idxs:
            ch = w_map.get(idx)
            if ch:
                rag_websites.append(ch["text"])
                rag_websites_examples.append({
                    "chunk_id": ch["id"],
                    "source_type": "website",
                    "source_id": ch["source_id"],
                    "text": ch["text"],
                })

    # Include latest LinkedIn/Trustpilot content (if any) as additional example context
    linkedin_texts = list(
        LinkedInScrape.objects.filter(user=request.user)
        .order_by("-created_at")
        .values_list("content", flat=True)[:1]
    )
    # Trim LinkedIn content to avoid overly large prompts
    linkedin_texts = [txt[:4000] for txt in linkedin_texts if isinstance(txt, str)]

    used_linkedin = bool(linkedin_texts)
    used_trustpilot = False
    linkedin_context_preview = (linkedin_texts[0][:800] if used_linkedin else "")
    trustpilot_context_preview = ""
    # Note: LinkedIn and Trustpilot are passed as separate context sections,
    # not merged into RAG lists

    messages = build_generation_messages(
        user_request=prompt,
        content_type=content_type,
        tone_guidelines=tone,
        terminology_guidelines=terminology,
        style_guidelines=style,
        content_rules=rules,
        similar_campaigns=rag_uploads,
        linkedin_context=linkedin_texts if used_linkedin else [],
        trustpilot_context=None,
        website_context=rag_websites,
    )

    # Prepare audit payload so the frontend can inspect exactly what was used
    brand_guidelines_out = {
        "tone": tone,
        "terminology": terminology,
        "style": style,
        "rules": rules,
    }

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
                return Response({
                    "reply": text,
                    "rag_uploads_examples": rag_uploads_examples,
                    "rag_websites_examples": rag_websites_examples,
                    "used_linkedin": used_linkedin,
                    "linkedin_context_preview": linkedin_context_preview,
                    "used_trustpilot": used_trustpilot,
                    "trustpilot_context_preview": trustpilot_context_preview,
                    "brand_guidelines": brand_guidelines_out,
                    "prompt_messages": messages,
                })
            else:
                return Response({
                    "reply": f"LLM error, echoing: {prompt}",
                    "error": resp.text,
                    "rag_uploads_examples": rag_uploads_examples,
                    "rag_websites_examples": rag_websites_examples,
                    "used_linkedin": used_linkedin,
                    "linkedin_context_preview": linkedin_context_preview,
                    "used_trustpilot": used_trustpilot,
                    "trustpilot_context_preview": trustpilot_context_preview,
                    "brand_guidelines": brand_guidelines_out,
                    "prompt_messages": messages,
                })
        except Exception as e:
            return Response({
                "reply": f"LLM error, echoing: {prompt}",
                "error": str(e),
                "rag_uploads_examples": rag_uploads_examples,
                "rag_websites_examples": rag_websites_examples,
                "used_linkedin": used_linkedin,
                "linkedin_context_preview": linkedin_context_preview,
                "used_trustpilot": used_trustpilot,
                "trustpilot_context_preview": trustpilot_context_preview,
                "brand_guidelines": brand_guidelines_out,
                "prompt_messages": messages,
            })

    # Fallback echo uses the constructed template context minimally
    combined_similar = (rag_uploads + rag_websites)
    synthetic = "\n\n".join([
        "[Tone] " + " | ".join(tone) if tone else "",
        "[Terminology] " + " | ".join(terminology) if terminology else "",
        "[Style] " + " | ".join(style) if style else "",
        "[Rules] " + " | ".join(rules) if rules else "",
        "[Similar] " + " | ".join(combined_similar) if combined_similar else "",
        "[Request] " + prompt,
    ])
    return Response({
        "reply": synthetic.strip(),
        "rag_uploads_examples": rag_uploads_examples,
        "rag_websites_examples": rag_websites_examples,
        "website_scrape_used": ({
            "id": latest_ws.id,
            "url": latest_ws.url,
            "created_at": latest_ws.created_at.isoformat(),
        } if latest_ws else None),
        "used_linkedin": used_linkedin,
        "linkedin_context_preview": linkedin_context_preview,
        "used_trustpilot": used_trustpilot,
        "trustpilot_context_preview": trustpilot_context_preview,
        "brand_guidelines": brand_guidelines_out,
        "prompt_messages": messages,
    })


