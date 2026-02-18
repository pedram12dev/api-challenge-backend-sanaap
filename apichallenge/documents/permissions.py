from rest_framework.permissions import BasePermission

from apichallenge.users.models import Role


class IsAdmin(BasePermission):
    """Full access: create users, assign roles, manage all documents."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsEditor(BasePermission):
    """Can upload and update documents but NOT delete."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.EDITOR)
        )


class IsViewer(BasePermission):
    """Can only retrieve / list documents."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.EDITOR, Role.VIEWER)
        )


class DocumentPermission(BasePermission):
    """
    Consolidated permission class for DocumentApi:
      - GET (list / retrieve / download): any authenticated user (viewer+)
      - POST / PUT / PATCH: editor+
      - DELETE: admin only
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if request.method in ("POST", "PUT", "PATCH"):
            return request.user.role in (Role.ADMIN, Role.EDITOR)

        if request.method == "DELETE":
            return request.user.role == Role.ADMIN

        return False
