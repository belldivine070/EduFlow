"""
Authentication & User Profile API v1 views.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import SchoolMembership, User
from core.constants import MEMBERSHIP_ACTIVE


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "is_platform_developer",
        ]
        read_only_fields = ["id", "username", "is_platform_developer"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Issues JWT access/refresh tokens only if the user is active and, when
    accessed via a school domain, holds an active membership in that school.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        request = self.context.get("request")
        school = getattr(request, "school", None) if request else None

        if not self.user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        membership_data = None
        school_data = None

        if school is not None:
            if not school.is_active:
                raise serializers.ValidationError(
                    "This school portal is currently deactivated. Please contact administration."
                )
            membership = SchoolMembership.objects.filter(
                school=school,
                user=self.user,
                status=MEMBERSHIP_ACTIVE,
            ).first()
            if not membership and not self.user.is_superuser:
                raise serializers.ValidationError(
                    "You do not have an active membership for this school."
                )
            if membership:
                membership_data = {
                    "id": str(membership.id),
                    "role": membership.role,
                    "role_display": membership.get_role_display(),
                    "status": membership.status,
                }
            school_data = {
                "id": str(school.id),
                "name": school.name,
                "code": school.code,
                "slug": school.slug,
            }

        data["user"] = UserProfileSerializer(self.user).data
        data["school"] = school_data
        data["membership"] = membership_data
        return data


class LoginAPIView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = TenantTokenObtainPairSerializer


class RefreshAPIView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid or already revoked refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = getattr(request, "school", None)
        membership = None
        if school:
            m = SchoolMembership.objects.filter(
                school=school, user=request.user, status=MEMBERSHIP_ACTIVE
            ).first()
            if m:
                membership = {
                    "id": str(m.id),
                    "role": m.role,
                    "role_display": m.get_role_display(),
                    "status": m.status,
                }
        return Response(
            {
                "user": UserProfileSerializer(request.user).data,
                "school": {
                    "id": str(school.id),
                    "name": school.name,
                    "code": school.code,
                    "slug": school.slug,
                } if school else None,
                "membership": membership,
            }
        )

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"user": serializer.data}, status=status.HTTP_200_OK)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")
        if not request.user.check_password(old_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
