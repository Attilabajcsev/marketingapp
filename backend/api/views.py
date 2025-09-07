from django.contrib.auth.models import User
from django.conf import settings
from .serializers import (
    UserSerializer,
    OAuthUserRegistrationSerializer,
    BrandGuidelineSerializer,
    UploadedCampaignSerializer,
    LinkedInScrapeSerializer,
    WebsiteScrapeSerializer,
)
from .models import BrandGuideline, UploadedCampaign, LinkedInScrape, WebsiteScrape
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
from urllib.parse import urljoin, urlparse, urlunparse

# Robust HTML decoding and extraction
from charset_normalizer import from_bytes as cn_from_bytes
from bs4 import BeautifulSoup
import trafilatura
import ftfy


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
    # Tolerate leading '@' copy-pastes
    url = url.lstrip('@ ')
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
    """Fetch a Trustpilot company URL and store extracted, high-quality review text for the user.
    Strategy:
      1) Normalize URL and prefer recency sort
      2) Try extracting reviews from Next.js __NEXT_DATA__ JSON
      3) Fallback to JSON-LD scripts with "review" arrays
      4) Fallback to DOM heuristics
      5) Crawl first 2-3 pages to collect more reviews
    """
    if request.method == "GET":
        obj = TrustpilotScrape.objects.filter(user=request.user).order_by("-created_at").first()
        if not obj:
            return Response({"detail": "No Trustpilot scrape found"}, status=204)
        data_resp = TrustpilotScrapeSerializer(obj).data
        data_resp["preview_texts"] = (obj.content or "").split("\n")[:20]
        return Response(data_resp)

    data = request.data or {}
    url = (data.get("url") or "").strip()
    if not url or "trustpilot." not in url:
        return Response({"error": "Please provide a valid Trustpilot URL."}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def fetch(u: str) -> str:
        r = http_requests.get(u, headers=headers, timeout=20)
        raw = r.content or b""
        try:
            best = cn_from_bytes(raw).best()
            text = best.output() if best else (r.text or "")
        except Exception:
            text = r.text or ""
        return ftfy.fix_text(text)

    def add_param(u: str, key: str, value: str) -> str:
        from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
        p = urlparse(u)
        q = dict(parse_qsl(p.query))
        q[key] = value
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))

    def extract_from_next_data(html: str) -> list[dict]:
        # Prefer robust DOM lookup over brittle regex
        s = BeautifulSoup(html, "lxml")
        tag = s.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return []
        try:
            obj = json.loads(tag.string)
        except Exception:
            return []
        reviews = []
        # Generic recursive finder for review-like nodes
        def rec(node):
            try:
                if isinstance(node, dict):
                    # common trustpilot fields
                    text = node.get("text") or node.get("bodyText") or node.get("reviewText") or node.get("content")
                    if isinstance(text, str) and len(text.strip()) > 60:
                        out = {"text": text}
                        if node.get("rating"):
                            out["rating"] = node.get("rating")
                        if node.get("ratingValue"):
                            out["rating"] = node.get("ratingValue")
                        if node.get("createdAt"):
                            out["date"] = node.get("createdAt")
                        if node.get("consumer") and isinstance(node.get("consumer"), dict):
                            nm = node["consumer"].get("displayName") or node["consumer"].get("name")
                            if nm:
                                out["author"] = nm
                        reviews.append(out)
                    for v in node.values():
                        rec(v)
                elif isinstance(node, list):
                    for v in node:
                        rec(v)
            except Exception:
                return
        rec(obj)
        # Try a few likely paths
        paths = [
            ["props", "pageProps", "businessUnit", "reviews"],
            ["props", "pageProps", "reviews"],
            ["props", "pageProps", "entities", "reviews"],
        ]
        for path in paths:
            cur = obj
            ok = True
            for k in path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False
                    break
            if ok:
                if isinstance(cur, dict):
                    # entities map
                    for rv in cur.values():
                        if isinstance(rv, dict):
                            reviews.append(rv)
                elif isinstance(cur, list):
                    reviews.extend([rv for rv in cur if isinstance(rv, dict)])
        return reviews

    def extract_from_ld_json(soup: BeautifulSoup) -> list[dict]:
        out = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data_json = json.loads(tag.string or "{}")
            except Exception:
                continue
            arr = []
            if isinstance(data_json, dict) and "review" in data_json and isinstance(data_json["review"], list):
                arr = data_json["review"]
            elif isinstance(data_json, list):
                for it in data_json:
                    if isinstance(it, dict) and "review" in it and isinstance(it["review"], list):
                        arr.extend(it["review"])
            for rv in arr:
                if isinstance(rv, dict):
                    out.append(rv)
        return out

    def extract_from_dom(soup: BeautifulSoup) -> list[dict]:
        reviews = []
        # Look for microdata
        for art in soup.find_all(attrs={"itemtype": re.compile("Review$", re.I)}):
            body = art.find(attrs={"itemprop": "reviewBody"})
            rating = art.find(attrs={"itemprop": "ratingValue"})
            author = art.find(attrs={"itemprop": "author"})
            date = art.find(attrs={"itemprop": "datePublished"})
            text = (body.get_text(" ", strip=True) if body else "").strip()
            if not text:
                continue
            reviews.append({
                "text": text,
                "rating": (rating.get_text(strip=True) if rating else None),
                "author": (author.get_text(strip=True) if author else None),
                "date": (date.get_text(strip=True) if date else None),
            })
        if reviews:
            return reviews
        # Heuristic by attributes/classes commonly used by Trustpilot
        candidates = []
        candidates.extend(soup.select('[data-service-review-id]'))
        candidates.extend(soup.select('[data-review-id]'))
        # fallback to likely class name patterns
        for div in soup.find_all(["article", "section", "div"]):
            cl = " ".join(div.get("class") or [])
            if re.search(r"review|ReviewCard|styles_reviewCard", cl, re.I):
                candidates.append(div)
        # de-dup candidates
        seen_nodes = set()
        uniq_candidates = []
        for c in candidates:
            key = id(c)
            if key in seen_nodes:
                continue
            seen_nodes.add(key)
            uniq_candidates.append(c)
        for c in uniq_candidates:
            txt = re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip()
            if txt and len(txt) > 80:
                reviews.append({"text": txt})
        return reviews

    def is_bot_challenge(html: str) -> bool:
        return bool(re.search(r"are you human|verify you are human|captcha", html, re.I))

    # Crawl a few pages
    pages = [url]
    # Prefer recency
    pages[0] = add_param(pages[0], "sort", "recency")
    pages[0] = add_param(pages[0], "languages", "da")
    for i in range(2, 4):  # pages 2-3
        pages.append(add_param(pages[0], "page", str(i)))

    collected: list[dict] = []
    last_html = ""
    for pu in pages:
        try:
            html = fetch(pu)
            last_html = html or last_html
        except Exception:
            continue
        if is_bot_challenge(html):
            # Return informative message without failing hard
            return Response({"url": url, "error": "Trustpilot presented a bot challenge. Please try again later or paste key reviews manually."}, status=200)
        soup = BeautifulSoup(html, "lxml")
        reviews = extract_from_next_data(html)
        if not reviews:
            reviews = extract_from_ld_json(soup)
        if not reviews:
            reviews = extract_from_dom(soup)
        for rv in reviews:
            text = str(rv.get("text") or rv.get("bodyText") or rv.get("title") or "").strip()
            if not text:
                continue
            rating = rv.get("rating") or (rv.get("ratingValue") if isinstance(rv.get("ratingValue"), str) else None)
            date = rv.get("dates") or rv.get("date") or rv.get("createdAt")
            author = rv.get("consumer") or rv.get("author")
            if isinstance(author, dict):
                author = author.get("displayName") or author.get("name")
            entry = {
                "text": ftfy.fix_text(text),
                "rating": rating,
                "date": date,
                "author": author,
            }
            collected.append(entry)
        if len(collected) >= 60:
            break

    # Deduplicate by text
    uniq = []
    seen = set()
    for rv in collected:
        t = rv["text"]
        key = t[:100]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(rv)

    if not uniq:
        # Final fallback: extract visible page text so user can at least inspect something
        if not last_html:
            return Response({"url": url, "error": "No review content could be extracted from this page."}, status=200)
        s2 = BeautifulSoup(last_html, "lxml")
        for t in s2(["script", "style", "noscript"]):
            t.decompose()
        fallback_text = re.sub(r"\s+", " ", s2.get_text(" ", strip=True)).strip()
        if len(fallback_text) > 500:
            full_text = fallback_text[:20000]
            obj = TrustpilotScrape.objects.create(user=request.user, url=url, content=full_text)
            data_resp = TrustpilotScrapeSerializer(obj).data
            # Provide a few slices for preview
            data_resp["preview_texts"] = [full_text[i:i+600] for i in range(0, min(len(full_text), 7200), 600)]
            return Response(data_resp, status=201)
        # Return gracefully so UI can display message without failing
        return Response({"url": url, "error": "No review content could be extracted from this page."}, status=200)

    # Compose a high-quality text block
    lines = []
    for i, rv in enumerate(uniq[:50], start=1):
        meta = []
        if rv.get("rating"):
            meta.append(f"{rv['rating']}★")
        if rv.get("author"):
            meta.append(str(rv["author"]))
        if rv.get("date"):
            meta.append(str(rv["date"]))
        suffix = f" ({', '.join(meta)})" if meta else ""
        lines.append(f"Review {i}\n" + rv["text"] + suffix)
    full_text = "\n\n".join(lines)
    if len(full_text) > 20000:
        full_text = full_text[:20000]

    obj = TrustpilotScrape.objects.create(user=request.user, url=url, content=full_text)
    data_resp = TrustpilotScrapeSerializer(obj).data
    data_resp["preview_texts"] = [rv["text"][:600] for rv in uniq[:12]]
    return Response(data_resp, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def website_scrape(request: Request) -> Response:
    """Given a blog index URL, robustly discover post links, fetch each, extract full main content,
    store full posts for auditing, and index cleaned text via vectorstore for RAG."""
    if request.method == "GET":
        obj = WebsiteScrape.objects.filter(user=request.user).order_by("-created_at").first()
        if not obj:
            return Response({"detail": "No Website scrape found"}, status=204)
        data_resp = WebsiteScrapeSerializer(obj).data
        # include lightweight previews of posts
        if isinstance(obj.posts, list) and obj.posts:
            data_resp["preview_posts"] = [
                {"url": p.get("url"), "title": p.get("title"), "sample": (p.get("text") or "")[:800]}
                for p in obj.posts[:10]
            ]
            # also include a small set of full posts for UI auditing
            data_resp["preview_posts_full"] = [
                {"url": p.get("url"), "title": p.get("title"), "text": p.get("text")}
                for p in obj.posts[:5]
            ]
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
    raw_url = (data.get("url") or "").strip()
    # Normalize common paste issues
    url = raw_url.strip().strip("'\"")
    url = url.rstrip(").,; \t\r\n")
    if not url:
        return Response({"error": "Please provide a valid website URL."}, status=400)
    if url.startswith("www."):
        url = "https://" + url
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    # IDN punycode for non-ASCII domains
    try:
        p = urlparse(url)
        if p.netloc:
            netloc_idna = p.netloc.encode("idna").decode("ascii")
            url = urlunparse((p.scheme, netloc_idna, p.path or "", p.params or "", p.query or "", p.fragment or ""))
    except Exception:
        pass

    def fetch_html(u: str) -> str:
        # Try a few strategies: https verify on, https verify off, http
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        attempts = []
        attempts.append((u, True))
        if u.startswith("https://"):
            attempts.append((u, False))
            attempts.append(("http://" + u[len("https://"):], True))
        else:
            attempts.append((u, False))
        last_exc = None
        for target, verify in attempts:
            try:
                r = http_requests.get(target, timeout=25, headers=headers, verify=verify)
                # proceed even if status is non-2xx
                raw = r.content or b""
                best = None
                try:
                    best = cn_from_bytes(raw).best()
                except Exception:
                    best = None
                decoded = best.output() if best else None
                text = decoded if decoded is not None else (r.text or "")
                # Ensure we always pass a str into ftfy
                if isinstance(text, bytes):
                    try:
                        text = text.decode(getattr(best, "encoding", "utf-8") or "utf-8", errors="replace")
                    except Exception:
                        text = text.decode("utf-8", errors="replace")
                try:
                    text = ftfy.fix_text(text)
                except Exception:
                    # If ftfy struggles, return decoded text as-is
                    pass
                return text
            except Exception as e:
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        return ""
        # Some sites return non-2xx to bots but still include readable HTML; proceed regardless of status.
        raw = r.content or b""
        decoded = None
        try:
            best = cn_from_bytes(raw).best()
            decoded = best.output() if best else None
        except Exception:
            decoded = None
        text = decoded or (r.text or "")
        # fix mojibake, ensure unicode normalization (handles Danish characters)
        text = ftfy.fix_text(text)
        return text

    def fetch_sitemap_candidates(base_url: str) -> list[str]:
        """Attempt to discover posts via common sitemap locations."""
        sitemap_urls = []
        try:
            p = urlparse(base_url)
            origin = f"{p.scheme}://{p.netloc}"
            sitemap_urls = [
                origin + "/sitemap.xml",
                origin + "/blog/sitemap.xml",
                origin + "/sitemap_index.xml",
            ]
        except Exception:
            pass
        found: list[str] = []
        for sm in sitemap_urls:
            try:
                xml_text = fetch_html(sm)
                if not xml_text:
                    continue
                sx = BeautifulSoup(xml_text, "xml")
                for loc in sx.find_all("loc"):
                    href = (loc.text or "").strip()
                    if not href:
                        continue
                    low = href.lower()
                    if any(seg in low for seg in ["blog", "post", "article", "news"]):
                        found.append(href)
            except Exception:
                continue
        return found

    try:
        index_html = fetch_html(url)
    except Exception as e:
        # Try sitemap discovery as fallback
        sitemap_found = fetch_sitemap_candidates(url)
        if not sitemap_found:
            return Response({"error": f"Could not fetch page and no sitemap found for {url}. {e}"}, status=200)
        index_html = ""

    # Discover post links using DOM signals
    soup = BeautifulSoup(index_html, "lxml")
    candidates: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(url, href)
        path = urlparse(full).path.lower()
        if any(seg in path for seg in [
            "blog", "post", "article", "news",
            # Common Danish sections
            "nyheder", "artikler", "viden"
        ]):
            candidates.append(full)

    # Fallback: links inside <article>, headings, or pagination blocks
    if not candidates:
        for art in soup.find_all(["main", "article", "section"]):
            for a in art.find_all("a", href=True):
                href = a["href"].strip()
                full = urljoin(url, href)
                path = urlparse(full).path.lower()
                if any(seg in path for seg in [
                    "blog", "post", "article", "news",
                    "nyheder", "artikler", "viden"
                ]):
                    candidates.append(full)

    # Fallback 2: RSS/Atom feeds advertised in <link rel="alternate"> if no obvious post links
    if not candidates:
        for l in soup.find_all("link", rel=True, href=True):
            rels = " ".join(l.get("rel") or [])
            typ = (l.get("type") or "").lower()
            if "alternate" in rels.lower() and any(x in typ for x in ("rss", "atom", "xml")):
                feed_url = urljoin(url, l["href"])
                try:
                    feed_html = fetch_html(feed_url)
                    feed_soup = BeautifulSoup(feed_html, "xml")
                    for item in feed_soup.find_all(["item", "entry"]):
                        link_tag = item.find("link")
                        href = None
                        if link_tag and link_tag.has_attr("href"):
                            href = link_tag["href"]
                        elif link_tag and link_tag.text:
                            href = link_tag.text
                        if href:
                            candidates.append(urljoin(url, href.strip()))
                except Exception:
                    pass

    # Fallback 3: sitemaps
    if not candidates:
        candidates = fetch_sitemap_candidates(url)

    # Deduplicate while preserving order and limit
    seen: set[str] = set()
    post_urls: list[str] = []
    # Heuristic: prefer likely article URLs and exclude category/index pages
    def looks_like_article(u: str) -> bool:
        pth = urlparse(u).path.strip("/")
        parts = [seg for seg in pth.split("/") if seg]
        if not parts:
            return False
        # require depth >= 2 for /blog/<slug>
        if "blog" in parts and len(parts) < 2:
            return False
        last = parts[-1]
        # article slugs tend to contain hyphens and be longer than 4 chars
        if len(last) >= 5 and ("-" in last or any(ch.isdigit() for ch in last)):
            return True
        # fallback to allow other structures
        return len(parts) >= 3

    filtered = [c for c in candidates if looks_like_article(c)] or candidates

    for c in filtered:
        if c not in seen:
            seen.add(c)
            post_urls.append(c)
        if len(post_urls) >= 20:
            break

    if not candidates:
        # Return gracefully with message so UI can show it
        return Response({"url": url, "error": "No blog-like links were discovered on this page or its sitemaps."}, status=200)

    # Before ingesting new site, delete previous website scrapes and their vectors for this user
    from vectorstore.models import VectorizedChunk
    WebsiteScrape.objects.filter(user=request.user).delete()
    VectorizedChunk.objects.filter(user=request.user, source_type="website").delete()

    # fetch each post, extract main content and index via vectorstore ingest
    from vectorstore.utils import sentence_split, text_to_vector
    from vectorstore.models import VectorizedChunk

    full_posts: list[dict] = []
    preview_texts: list[str] = []

    for purl in post_urls:
        try:
            phtml = fetch_html(purl)
            # Prefer trafilatura's robust main-content extraction
            extracted = trafilatura.extract(
                phtml,
                include_comments=False,
                include_tables=False,
                favor_recall=True,
                url=purl,
            )
            if not extracted:
                # fallback to visible-text via BeautifulSoup
                s = BeautifulSoup(phtml, "lxml")
                for tag in s(["script", "style", "noscript"]):
                    tag.decompose()
                text_nodes = s.get_text("\n")
                extracted = re.sub(r"\s+", " ", text_nodes).strip()

            # Normalize/fix text and cap to a reasonable size
            ptext = ftfy.fix_text(extracted).strip()
            if not ptext:
                continue

            # Derive a reasonable title
            st = BeautifulSoup(phtml, "lxml")
            title_tag = st.find("h1") or st.find("title")
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"

            # Collect post for auditing UI
            full_posts.append({"url": purl, "title": title, "text": ptext})

            # Ingest: treat each full post as multiple chunks
            chunks = sentence_split(ptext)
            for ch in chunks:
                if not ch.strip():
                    continue
                VectorizedChunk.objects.create(
                    user=request.user,
                    source_type="website",
                    source_id=0,  # temporary; reassigned after obj exists
                    text=ch,
                    vector=text_to_vector(ch),
                )
                if len(preview_texts) < 20:
                    preview_texts.append(ch)
        except Exception:
            continue

    # Create WebsiteScrape record and backfill source_id on chunks belonging to this scrape
    obj = WebsiteScrape.objects.create(user=request.user, url=url, post_urls=post_urls, posts=full_posts)

    # Update chunks created above to reference the new obj.id
    VectorizedChunk.objects.filter(user=request.user, source_type="website", source_id=0).update(source_id=obj.id)

    payload = WebsiteScrapeSerializer(obj).data
    payload["preview_texts"] = preview_texts
    # lightweight previews of posts for UI auditing
    payload["preview_posts"] = [
        {"url": p["url"], "title": p["title"], "sample": p["text"][:800]}
        for p in (full_posts[:10] if full_posts else [])
    ]
    # include a small number of full posts to inspect complete content
    payload["preview_posts_full"] = [
        {"url": p["url"], "title": p["title"], "text": p["text"]}
        for p in (full_posts[:5] if full_posts else [])
    ]
    return Response(payload, status=201)
