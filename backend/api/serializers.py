from django.contrib.auth.models import User
from rest_framework import serializers
from .models import BrandGuideline, UploadedCampaign, LinkedInScrape, TrustpilotScrape, WebsiteScrape


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class OAuthUserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer only used for Google OAuth logins. Same as UserSerializer but we don't expect password from user. We use unusable password instead.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        return user


class BrandGuidelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandGuideline
        fields = ["id", "title", "content", "guideline_type", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError(
                "Authentication required to create brand guidelines."
            )
        return BrandGuideline.objects.create(user=request.user, **validated_data)


class UploadedCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedCampaign
        fields = [
            "id",
            "filename",
            "file_type",
            "raw_content",
            "parsed_campaigns",
            "upload_date",
            "campaign_count",
        ]
        read_only_fields = ["id", "upload_date", "campaign_count"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError(
                "Authentication required to upload campaigns."
            )
        return UploadedCampaign.objects.create(user=request.user, **validated_data)


class LinkedInScrapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInScrape
        fields = ["id", "url", "content", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError("Authentication required.")
        return LinkedInScrape.objects.create(user=request.user, **validated_data)


class TrustpilotScrapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustpilotScrape
        fields = ["id", "url", "content", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError("Authentication required.")
        return TrustpilotScrape.objects.create(user=request.user, **validated_data)


class WebsiteScrapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteScrape
        fields = ["id", "url", "post_urls", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError("Authentication required.")
        return WebsiteScrape.objects.create(user=request.user, **validated_data)
