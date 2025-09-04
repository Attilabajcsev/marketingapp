from django.contrib.auth.models import User
from django.conf import settings
from .serializers import (
    UserSerializer,
    OAuthUserRegistrationSerializer,
    BrandGuidelineSerializer,
    UploadedCampaignSerializer,
)
from .models import BrandGuideline, UploadedCampaign
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
