from django.contrib.auth.models import User
from rest_framework import serializers
from .models import EmailCampaign


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


class EmailCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailCampaign
        fields = ["id", "title", "content", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError(
                "Authentication required to create email campaigns."
            )
        return EmailCampaign.objects.create(user=request.user, **validated_data)
