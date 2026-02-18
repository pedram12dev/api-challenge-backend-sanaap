from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apichallenge.api.mixins import ApiAuthMixin
from apichallenge.api.pagination import (
    LimitOffsetPagination,
    get_paginated_response,
)
from apichallenge.documents.models import Document, AuditLog
from apichallenge.documents.permissions import DocumentPermission, IsAdmin
from apichallenge.documents.selectors import document_list, document_get, audit_log_list
from apichallenge.documents.services import (
    document_create,
    document_update,
    document_delete,
    create_audit_log,
)
from apichallenge.documents.tasks import process_document_after_upload
from apichallenge.users.models import BaseUser, Role


class BinaryFileRenderer(BaseRenderer):
    """Renderer that passes binary file data through without modification."""
    media_type = "application/octet-stream"
    format = "bin"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def _get_document_or_404(pk: int) -> Document:
    """Get document from cached selector or raise 404."""
    doc = document_get(pk=pk)
    if doc is None:
        raise Http404
    return doc


class DocumentOutputSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "description",
            "file_name",
            "file_size",
            "content_type",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
            "updated_at",
        )


class DocumentDetailOutputSerializer(DocumentOutputSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta(DocumentOutputSerializer.Meta):
        fields = DocumentOutputSerializer.Meta.fields + ("file_url",)

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(f"/api/documents/{obj.id}/download/")
        return None


class DocumentCreateInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="")
    file = serializers.FileField()

    def validate_file(self, value):
        # Max 50 MB
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 50 MB.")
        return value


class DocumentUpdateInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    file = serializers.FileField(required=False)


class AuditLogOutputSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "username",
            "document",
            "action",
            "document_title",
            "ip_address",
            "details",
            "timestamp",
        )


class AdminUserCreateInputSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8)
    role = serializers.ChoiceField(choices=Role.choices)


class AdminUserOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseUser
        fields = ("id", "username", "role", "is_active", "created_at")


class AdminUserUpdateRoleInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices)



@extend_schema(tags=["Documents"])
class DocumentListCreateApi(ApiAuthMixin, APIView):
    """
    GET  → List all documents (viewer+) with filtering & pagination.
    POST → Upload a new document (editor+).
    """

    permission_classes = (DocumentPermission,)
    parser_classes = (MultiPartParser, FormParser)

    class Pagination(LimitOffsetPagination):
        default_limit = 10

    @extend_schema(
        parameters=[
            OpenApiParameter("title", OpenApiTypes.STR, description="Filter by title (contains)"),
            OpenApiParameter("content_type", OpenApiTypes.STR, description="Filter by content type"),
            OpenApiParameter("uploaded_by", OpenApiTypes.INT, description="Filter by uploader ID"),
            OpenApiParameter("created_after", OpenApiTypes.DATETIME, description="Created after"),
            OpenApiParameter("created_before", OpenApiTypes.DATETIME, description="Created before"),
            OpenApiParameter("limit", OpenApiTypes.INT, description="Pagination limit"),
            OpenApiParameter("offset", OpenApiTypes.INT, description="Pagination offset"),
        ],
        responses=DocumentOutputSerializer(many=True),
    )
    def get(self, request):
        documents = document_list(filters=request.query_params)
        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=DocumentOutputSerializer,
            queryset=documents,
            request=request,
            view=self,
        )

    @extend_schema(
        request=DocumentCreateInputSerializer,
        responses={201: DocumentDetailOutputSerializer},
    )
    def post(self, request):
        serializer = DocumentCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = document_create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            file=serializer.validated_data["file"],
            uploaded_by=request.user,
            request=request,
        )

        # Trigger background processing
        process_document_after_upload.delay(document.id)

        output = DocumentDetailOutputSerializer(document, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)



@extend_schema(tags=["Documents"])
class DocumentDetailApi(ApiAuthMixin, APIView):
    """
    GET    → Retrieve document details (viewer+).
    PUT    → Update document (editor+).
    DELETE → Delete document (admin only).
    """

    permission_classes = (DocumentPermission,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(responses=DocumentDetailOutputSerializer)
    def get(self, request, pk):
        document = _get_document_or_404(pk)

        create_audit_log(
            user=request.user,
            document=document,
            action=AuditLog.Action.READ,
            request=request,
        )

        output = DocumentDetailOutputSerializer(document, context={"request": request})
        return Response(output.data)

    @extend_schema(
        request=DocumentUpdateInputSerializer,
        responses=DocumentDetailOutputSerializer,
    )
    def put(self, request, pk):
        document = _get_document_or_404(pk)

        serializer = DocumentUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = document_update(
            document=document,
            title=serializer.validated_data.get("title"),
            description=serializer.validated_data.get("description"),
            file=serializer.validated_data.get("file"),
            updated_by=request.user,
            request=request,
        )

        if serializer.validated_data.get("file"):
            process_document_after_upload.delay(document.id)

        output = DocumentDetailOutputSerializer(document, context={"request": request})
        return Response(output.data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        document = _get_document_or_404(pk)

        document_delete(
            document=document,
            deleted_by=request.user,
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)



@extend_schema(tags=["Documents"])
class DocumentDownloadApi(ApiAuthMixin, APIView):
    """Secure file download endpoint (viewer+)."""

    permission_classes = (DocumentPermission,)
    renderer_classes = (BinaryFileRenderer,)

    @extend_schema(
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    def get(self, request, pk):
        document = _get_document_or_404(pk)

        create_audit_log(
            user=request.user,
            document=document,
            action=AuditLog.Action.DOWNLOAD,
            request=request,
        )

        response = FileResponse(
            document.file.open("rb"),
            content_type=document.content_type or "application/octet-stream",
        )
        response["Content-Disposition"] = f'attachment; filename="{document.file_name}"'
        return response



@extend_schema(tags=["Admin"])
class AuditLogListApi(ApiAuthMixin, APIView):
    """List audit logs (admin only)."""

    permission_classes = (IsAdmin,)

    class Pagination(LimitOffsetPagination):
        default_limit = 20

    @extend_schema(
        parameters=[
            OpenApiParameter("document_id", OpenApiTypes.INT, description="Filter by document ID"),
            OpenApiParameter("limit", OpenApiTypes.INT),
            OpenApiParameter("offset", OpenApiTypes.INT),
        ],
        responses=AuditLogOutputSerializer(many=True),
    )
    def get(self, request):
        document_id = request.query_params.get("document_id")
        logs = audit_log_list(
            document_id=int(document_id) if document_id else None,
        )
        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=AuditLogOutputSerializer,
            queryset=logs,
            request=request,
            view=self,
        )


@extend_schema(tags=["Admin"])
class AdminUserListCreateApi(ApiAuthMixin, APIView):
    """
    Admin-only: List all users or create a new user with a role.
    """

    permission_classes = (IsAdmin,)

    @extend_schema(responses=AdminUserOutputSerializer(many=True))
    def get(self, request):
        users = BaseUser.objects.all().order_by("-created_at")
        output = AdminUserOutputSerializer(users, many=True)
        return Response(output.data)

    @extend_schema(
        request=AdminUserCreateInputSerializer,
        responses={201: AdminUserOutputSerializer},
    )
    def post(self, request):
        serializer = AdminUserCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = BaseUser.objects.create_user(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            role=serializer.validated_data["role"],
        )

        output = AdminUserOutputSerializer(user)
        return Response(output.data, status=status.HTTP_201_CREATED)



@extend_schema(tags=["Admin"])
class AdminUserRoleUpdateApi(ApiAuthMixin, APIView):
    """Admin-only: Update a user's role."""

    permission_classes = (IsAdmin,)

    @extend_schema(
        request=AdminUserUpdateRoleInputSerializer,
        responses=AdminUserOutputSerializer,
    )
    def patch(self, request, user_id):
        user = get_object_or_404(BaseUser, pk=user_id)

        serializer = AdminUserUpdateRoleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.role = serializer.validated_data["role"]
        user.save(update_fields=["role"])

        output = AdminUserOutputSerializer(user)
        return Response(output.data)
