from django.urls import path

from apichallenge.documents.apis import (
    DocumentListCreateApi,
    DocumentDetailApi,
    DocumentDownloadApi,
    AuditLogListApi,
    AdminUserListCreateApi,
    AdminUserRoleUpdateApi,
)

urlpatterns = [
    # Document CRUD
    path("", DocumentListCreateApi.as_view(), name="document-list-create"),
    path("<int:pk>/", DocumentDetailApi.as_view(), name="document-detail"),
    path("<int:pk>/download/", DocumentDownloadApi.as_view(), name="document-download"),

    # Audit logs (admin only)
    path("audit-logs/", AuditLogListApi.as_view(), name="audit-log-list"),

    # Admin: user management
    path("admin/users/", AdminUserListCreateApi.as_view(), name="admin-user-list-create"),
    path(
        "admin/users/<int:user_id>/role/",
        AdminUserRoleUpdateApi.as_view(),
        name="admin-user-role-update",
    ),
]
