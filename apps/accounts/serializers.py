from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .roles import user_role


class StaffLoginSerializer(TokenObtainPairSerializer):
    """Login serializer that enriches the JWT response with role and profile."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user_role(user)
        token['full_name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = StaffMeSerializer(self.user).data
        return data


class StaffMeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def get_role(self, obj) -> str | None:
        return user_role(obj)

    def get_groups(self, obj) -> list[str]:
        return list(obj.groups.values_list('name', flat=True))
