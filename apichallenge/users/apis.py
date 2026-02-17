from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from django.core.validators import MinLengthValidator

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken

from apichallenge.users.models import BaseUser
from apichallenge.users.services import register
from .validators import number_validator, special_char_validator, letter_validator


class RegisterApi(APIView):

    class InputRegisterSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        password = serializers.CharField(
            validators=[
                number_validator,
                letter_validator,
                special_char_validator,
                MinLengthValidator(limit_value=10),
            ]
        )
        confirm_password = serializers.CharField(max_length=255)

        def validate_username(self, username):
            if BaseUser.objects.filter(username=username).exists():
                raise serializers.ValidationError("This username is already taken.")
            return username

        def validate(self, data):
            if not data.get("password") or not data.get("confirm_password"):
                raise serializers.ValidationError("Please fill password and confirm password")

            if data.get("password") != data.get("confirm_password"):
                raise serializers.ValidationError("confirm password is not equal to password")
            return data

    class OutPutRegisterSerializer(serializers.ModelSerializer):
        token = serializers.SerializerMethodField("get_token")

        class Meta:
            model = BaseUser
            fields = ("username", "token", "created_at", "updated_at")

        def get_token(self, user):
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

    @extend_schema(request=InputRegisterSerializer, responses=OutPutRegisterSerializer)
    def post(self, request):
        serializer = self.InputRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = register(
                username=serializer.validated_data.get("username"),
                password=serializer.validated_data.get("password"),
            )
        except Exception as ex:
            return Response(
                f"Database Error {ex}",
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.OutPutRegisterSerializer(user, context={"request": request}).data)
