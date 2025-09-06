from django.contrib.auth.models import User
from django.conf import settings
from .serializers import (
    UserSerializer,
    OAuthUserRegistrationSerializer,
    BrandGuidelineSerializer,
    UploadedCampaignSerializer,
    LinkedInScrapeSerializer,
    TrustpilotScrapeSerializer,
    WebsiteScrapeSerializer,
)
from .models import BrandGuideline, UploadedCampaign, LinkedInScrape, TrustpilotScrape, WebsiteScrape
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.request import Request
from rest_framework import status
import csv as pycsv
import json
from typing import Any
import requests as http_requests
import re
import html as html_lib


@api_view(["POST"])
@permission_classes([AllowAny])
def create_user(request: Request) -> Response:
    """
    Creates user to the database.
    Endpoint: register/

    Request body:
        - username
        - email
        - first_name
        - last_name
        - password

    Returns:
        - id
        - username
    """
    serializer = UserSerializer(data=request.data)

    if serializer.is_valid():
        user: User = serializer.save()
        return Response(
            {
                "id": user.id,
                "username": user.username,
            },
            status=201,
        )

    print(f"Validation errors: {serializer.errors}")
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request: Request) -> Response:
    """
    Gets user profile information
    Endpoint: user/profile/

    Returns:
        - id
        - username
        - email
        - first_name
        - last_name
    """
    try:
        user: User = request.user
        serializer = UserSerializer(user)

        return Response(serializer.data)

    except Exception as e:
        print(f"Validation errors: {str(e)}")
        return Response({"error": "Internal server error"}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_google(request: Request) -> Response:
    """
    Verifies Google Auth token and creates User in the database.
    Endpoint: oauth-google/

    Request body:
        - id_token: token recieved on successful Google OAuth

    Returns:
        - access: JWT access token
        - refresh: JWT refresh token
    """

    data: dict[str, Any] = json.loads(request.body)
    google_token: str | None = data.get("id_token")

    if not google_token:
        return Response({"error": "Google token not provided"}, status=400)

    try:
        userinfo: dict[str, Any] = id_token.verify_oauth2_token(
            google_token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email: str = userinfo["email"]

        user: User = User.objects.filter(email=email).first()

        if not user:
            user_data: dict[str, str] = {
                "username": email,
                "email": email,
                "first_name": userinfo.get("given_name", ""),
                "last_name": userinfo.get("family_name", ""),
            }

            serializer = OAuthUserRegistrationSerializer(
                data=user_data
            )  # Creates new user with default user sync settings and basic user tier
            if serializer.is_valid():
                user = serializer.save()
            else:
                return Response(serializer.errors, status=400)

        # Generate JWT tokens for user
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})

    except ValueError:
        return Response(
            {"error": "Invalid token or token verification failed"}, status=401
        )
    except Exception as e:
        return Response({"error": f"Authentication failed: {str(e)}"}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def brand_guidelines_list(request: Request) -> Response:
    """
    Returns all brand guidelines for the authenticated user.
    Endpoint: brand-guidelines/
    """
    guidelines = BrandGuideline.objects.filter(user=request.user).order_by(
        "-uploaded_at", "-id"
    )
    serializer = BrandGuidelineSerializer(guidelines, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def brand_guidelines_create(request: Request) -> Response:
    """
    Creates a new brand guideline for the authenticated user.
    Endpoint: brand-guidelines/

    Request body:
      - title: string
      - content: string
    """
    serializer = BrandGuidelineSerializer(
        data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        guideline = serializer.save()
        return Response(BrandGuidelineSerializer(guideline).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def brand_guideline_detail(request: Request, guideline_id: int) -> Response:
    """
    Update or delete a single brand guideline for the authenticated user.
    Endpoint: brand-guidelines/<guideline_id>/
    """
    guideline = BrandGuideline.objects.filter(id=guideline_id, user=request.user).first()
    if not guideline:
        return Response({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        guideline.delete()
        return Response(status=204)

    # PUT update
    serializer = BrandGuidelineSerializer(
        guideline, data=request.data, partial=True, context={"request": request}
    )
    if serializer.is_valid():
        updated = serializer.save()
        return Response(BrandGuidelineSerializer(updated).data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def uploaded_campaigns_list(request: Request) -> Response:
    """
    Returns metadata about uploaded campaign files for the authenticated user.
    Endpoint: uploaded-campaigns/
    """
    uploads = UploadedCampaign.objects.filter(user=request.user).order_by(
        "-upload_date", "-id"
    )
    serializer = UploadedCampaignSerializer(uploads, many=True)
    return Response(serializer.data)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def uploaded_campaign_detail(request: Request, upload_id: int) -> Response:
    """
    Returns or deletes a single upload for the authenticated user.
    Endpoint: uploaded-campaigns/<upload_id>/
    """
    upload = UploadedCampaign.objects.filter(id=upload_id, user=request.user).first()
    if not upload:
        return Response({"error": "Not found"}, status=404)
    if request.method == "DELETE":
        upload.delete()
        return Response(status=204)
    return Response(UploadedCampaignSerializer(upload).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_campaign_file(request: Request) -> Response:
    """
    Accepts multipart/form-data with 'file' field, size <= 5MB.
    Auto-detects file_type from extension and stores raw content.
    Endpoint: uploaded-campaigns/upload/
    """
    if "file" not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    upload = request.FILES["file"]
    max_size = 5 * 1024 * 1024
    if upload.size > max_size:
        return Response({"error": "File too large (max 5MB)"}, status=status.HTTP_400_BAD_REQUEST)

    filename: str = upload.name
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["csv", "txt", "json"]:
        return Response({"error": "Unsupported file type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        raw_bytes = upload.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return Response({"error": "Failed to read file"}, status=status.HTTP_400_BAD_REQUEST)

    # Parse campaigns based on file type
    def _normalize_record(record: dict) -> dict:
        title = (
            record.get("title")
            or record.get("subject")
            or record.get("Subject")
            or record.get("Title")
            or "Untitled"
        )
        content = (
            record.get("content")
            or record.get("body")
            or record.get("Body")
            or record.get("Content")
            or ""
        )
        normalized = {"title": str(title).strip(), "content": str(content).strip()}
        # include other keys as metadata if present
        extras = {k: v for k, v in record.items() if k not in ["title", "subject", "Subject", "Title", "content", "body", "Body", "Content"]}
        if extras:
            normalized["meta"] = extras
        return normalized

    def parse_csv(text: str) -> list[dict]:
        try:
            rows = list(pycsv.DictReader(text.splitlines()))
            return [_normalize_record(r) for r in rows if any(v for v in r.values())]
        except Exception:
            return []

    def parse_txt(text: str) -> list[dict]:
        # Heuristics: split on lines of dashes/equals or two+ blank lines
        import re

        blocks = re.split(r"\n\s*[-=]{3,}\s*\n|\n{2,}", text.strip())
        items = []
        for block in blocks:
            b = block.strip()
            if not b:
                continue
            lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
            if not lines:
                continue
            title = lines[0][:120]
            content = "\n".join(lines[1:]) if len(lines) > 1 else ""
            items.append({"title": title, "content": content})
        return items

    def parse_json(text: str) -> list[dict]:
        try:
            data = json.loads(text)
        except Exception:
            return []
        records: list[dict] = []
        if isinstance(data, list):
            records = [r for r in data if isinstance(r, dict)]
        elif isinstance(data, dict):
            if isinstance(data.get("campaigns"), list):
                records = [r for r in data.get("campaigns") if isinstance(r, dict)]
            else:
                records = [data]
        return [_normalize_record(r) for r in records]

    parsed: list[dict]
    if ext == "csv":
        parsed = parse_csv(raw_text)
    elif ext == "txt":
        parsed = parse_txt(raw_text)
    else:
        parsed = parse_json(raw_text)

    created = UploadedCampaign.objects.create(
        user=request.user,
        filename=filename,
        file_type=ext,
        raw_content=raw_text,
        parsed_campaigns=parsed,
        campaign_count=len(parsed),
    )
    return Response(UploadedCampaignSerializer(created).data, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def linkedin_scrape(request: Request) -> Response:
    """Fetch a LinkedIn company URL and store raw content for the user."""
    if request.method == "GET":
        obj = LinkedInScrape.objects.filter(user=request.user).order_by("-created_at").first()
        if not obj:
            return Response({"detail": "No LinkedIn scrape found"}, status=204)
        data = LinkedInScrapeSerializer(obj).data
        data["preview_texts"] = [obj.content[:1000]] if obj.content else []
        return Response(data)

    data = request.data or {}
    url = (data.get("url") or "").strip()
    # tolerate leading '@' copy-pastes
    url = url.lstrip('@ ')
    if not url or "linkedin.com" not in url:
        return Response({"error": "Please provide a valid LinkedIn URL."}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        resp = http_requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            },
        )
        if not resp.ok:
            return Response({"error": f"Failed to fetch page: {resp.status_code}"}, status=400)
        html = resp.text or ""
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    # Heuristic HTML -> text extraction (no external parsers to keep deps minimal)
    def _extract_visible_text(doc: str) -> str:
        if not doc:
            return ""
        # drop scripts/styles
        doc = re.sub(r"<script[\s\S]*?</script>", " ", doc, flags=re.IGNORECASE)
        doc = re.sub(r"<style[\s\S]*?</style>", " ", doc, flags=re.IGNORECASE)
        # remove tags
        doc = re.sub(r"<[^>]+>", " ", doc)
        # unescape entities
        doc = html_lib.unescape(doc)
        # collapse whitespace
        doc = re.sub(r"\s+", " ", doc).strip()
        return doc

    text = _extract_visible_text(html)

    # If we clearly hit a login wall, try fallback to company root/about page
    if re.search(r"LinkedIn\s+Login|Sign in \| LinkedIn", text, flags=re.IGNORECASE):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            parts = parsed.path.split('/')
            # find '/company/{slug}' prefix
            if 'company' in parts:
                idx = parts.index('company')
                base_path = '/'.join(parts[: idx + 2])  # /company/{slug}
                fallback_url = f"{parsed.scheme or 'https'}://{parsed.netloc}{base_path}"
                fresp = http_requests.get(fallback_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if fresp.ok:
                    ftext = _extract_visible_text(fresp.text or "")
                    if ftext:
                        text = ftext
        except Exception:
            pass

    if not text:
        return Response({
            "error": "LinkedIn returned no public content; try a public About page or paste text manually.",
        }, status=400)

    # Keep a reasonable cap
    if len(text) > 20000:
        text = text[:20000]

    obj = LinkedInScrape.objects.create(user=request.user, url=url, content=text)
    data = LinkedInScrapeSerializer(obj).data
    # provide small preview
    data["preview_texts"] = [text[:1000]] if text else []
    return Response(data, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def trustpilot_scrape(request: Request) -> Response:
    """Fetch a Trustpilot company URL and store extracted review text for the user."""
    if request.method == "GET":
        obj = TrustpilotScrape.objects.filter(user=request.user).order_by("-created_at").first()
        if not obj:
            return Response({"detail": "No Trustpilot scrape found"}, status=204)
        data_resp = TrustpilotScrapeSerializer(obj).data
        data_resp["preview_texts"] = (obj.content or "").split("\n")[:20]
        return Response(data_resp)

    data = request.data or {}
    url = (data.get("url") or "").strip()
    if not url or "trustpilot.com" not in url:
        return Response({"error": "Please provide a valid Trustpilot URL."}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        resp = http_requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            },
        )
        if not resp.ok:
            return Response({"error": f"Failed to fetch page: {resp.status_code}"}, status=400)
        html = resp.text or ""
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    # Heuristic extraction similar to LinkedIn, tuned for reviews
    def _extract_reviews(doc: str) -> str:
        if not doc:
            return ""
        doc = re.sub(r"<script[\s\S]*?</script>", " ", doc, flags=re.IGNORECASE)
        doc = re.sub(r"<style[\s\S]*?</style>", " ", doc, flags=re.IGNORECASE)
        doc = re.sub(r"<br\s*/?>", "\n", doc, flags=re.IGNORECASE)
        doc = re.sub(r"</p>", "\n", doc, flags=re.IGNORECASE)
        doc = re.sub(r"<[^>]+>", " ", doc)
        doc = html_lib.unescape(doc)
        # basic segmentation
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in doc.split("\n")]
        lines = [ln for ln in lines if ln]
        keep = []
        for ln in lines:
            # ignore nav/footer/legal
            if re.search(r"Trustpilot|Log in|Sign up|Categories|Business|Claimed|Cookies|Privacy|Terms", ln, re.IGNORECASE):
                continue
            if len(ln) < 20:
                continue
            keep.append(ln)
        text = "\n".join(keep)
        return text.strip()

    text = _extract_reviews(html)
    if not text:
        return Response({"error": "No review content could be extracted from this page."}, status=400)
    if len(text) > 20000:
        text = text[:20000]

    obj = TrustpilotScrape.objects.create(user=request.user, url=url, content=text)
    data = TrustpilotScrapeSerializer(obj).data
    data["preview_texts"] = text.split("\n")[:20]
    return Response(data, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def website_scrape(request: Request) -> Response:
    """Given a blog index URL, discover post links, fetch each, chunk and index via vectorstore."""
    if request.method == "GET":
        obj = WebsiteScrape.objects.filter(user=request.user).order_by("-created_at").first()
        if not obj:
            return Response({"detail": "No Website scrape found"}, status=204)
        data_resp = WebsiteScrapeSerializer(obj).data
        # collect a small sample of recent website chunks
        from vectorstore.models import VectorizedChunk
        chunks = list(
            VectorizedChunk.objects.filter(user=request.user, source_type="website", source_id=obj.id)
            .order_by("-id")
            .values_list("text", flat=True)[:20]
        )
        data_resp["preview_texts"] = chunks
        return Response(data_resp)

    data = request.data or {}
    url = (data.get("url") or "").strip()
    if not url:
        return Response({"error": "Please provide a valid website URL."}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        resp = http_requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if not resp.ok:
            return Response({"error": f"Failed to fetch page: {resp.status_code}"}, status=400)
        html = resp.text or ""
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    # naive link extraction to blog posts (looks for /blog/ or article links)
    links = re.findall(r"href=\"([^\"]+)\"", html)
    def _abs(u: str) -> str:
        if u.startswith("http://") or u.startswith("https://"):
            return u
        from urllib.parse import urljoin
        return urljoin(url, u)

    cand = []
    for ln in links:
        if any(k in ln.lower() for k in ["/blog/", "/posts/", "/article", "/news/"]):
            cand.append(_abs(ln))
    # de-dup and cap
    seen = set()
    post_urls: list[str] = []
    for c in cand:
        if c not in seen:
            seen.add(c)
            post_urls.append(c)
        if len(post_urls) >= 15:
            break

    # fetch each post, extract text and index via vectorstore ingest
    from vectorstore.utils import sentence_split, text_to_vector
    from vectorstore.models import VectorizedChunk

    # create WebsiteScrape record first to associate chunks
    obj = WebsiteScrape.objects.create(user=request.user, url=url, post_urls=post_urls)

    preview_texts: list[str] = []
    for purl in post_urls:
        try:
            pr = http_requests.get(purl, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if not pr.ok:
                continue
            phtml = pr.text or ""
            # very simple text extraction
            ptext = re.sub(r"<script[\s\S]*?</script>", " ", phtml, flags=re.IGNORECASE)
            ptext = re.sub(r"<style[\s\S]*?</style>", " ", ptext, flags=re.IGNORECASE)
            ptext = re.sub(r"<br\s*/?>", "\n", ptext, flags=re.IGNORECASE)
            ptext = re.sub(r"</p>", "\n", ptext, flags=re.IGNORECASE)
            ptext = re.sub(r"<[^>]+>", " ", ptext)
            ptext = html_lib.unescape(ptext)
            ptext = re.sub(r"\s+", " ", ptext).strip()
            if not ptext:
                continue
            # ingest: we treat each discovered post as an "upload"-like unit for RAG
            chunks = sentence_split(ptext)
            for ch in chunks:
                if not ch.strip():
                    continue
                VectorizedChunk.objects.create(
                    user=request.user,
                    source_type="website",
                    source_id=obj.id,
                    text=ch,
                    vector=text_to_vector(ch),
                )
                if len(preview_texts) < 20:
                    preview_texts.append(ch)
        except Exception:
            continue

    payload = WebsiteScrapeSerializer(obj).data
    payload["preview_texts"] = preview_texts
    return Response(payload, status=201)
