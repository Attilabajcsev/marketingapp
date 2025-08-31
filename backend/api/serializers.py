from django.contrib.auth.models import User
from rest_framework import serializers


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
