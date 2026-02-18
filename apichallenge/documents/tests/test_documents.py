from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apichallenge.users.models import BaseUser, Role
from apichallenge.documents.models import Document, AuditLog
from apichallenge.documents.services import (
    document_create,
    document_update,
    document_delete,
)


def _make_file(name="test.txt", content=b"hello world", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class DocumentServiceTests(TestCase):
    """Test service layer (business logic)."""

    def setUp(self):
        self.admin = BaseUser.objects.create_user(
            username="admin", password="Admin@12345", role=Role.ADMIN
        )
        self.editor = BaseUser.objects.create_user(
            username="editor", password="Editor@12345", role=Role.EDITOR
        )

    def test_create_document(self):
        doc = document_create(title="Test Doc", file=_make_file(), uploaded_by=self.admin)
        self.assertEqual(doc.title, "Test Doc")
        self.assertEqual(doc.file_name, "test.txt")
        self.assertEqual(doc.file_size, 11)
        self.assertEqual(doc.uploaded_by, self.admin)

    def test_create_audit_log_on_create(self):
        doc = document_create(title="Audit", file=_make_file(), uploaded_by=self.editor)
        logs = AuditLog.objects.filter(document=doc, action=AuditLog.Action.CREATE)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.editor)

    def test_update_document(self):
        doc = document_create(title="Original", file=_make_file(), uploaded_by=self.admin)
        updated = document_update(document=doc, title="Updated", updated_by=self.admin)
        self.assertEqual(updated.title, "Updated")

    def test_update_audit_log(self):
        doc = document_create(title="Before", file=_make_file(), uploaded_by=self.admin)
        document_update(document=doc, title="After", updated_by=self.admin)
        self.assertEqual(
            AuditLog.objects.filter(document=doc, action=AuditLog.Action.UPDATE).count(), 1
        )

    def test_delete_document(self):
        doc = document_create(title="Delete Me", file=_make_file(), uploaded_by=self.admin)
        doc_id = doc.id
        document_delete(document=doc, deleted_by=self.admin)
        self.assertFalse(Document.objects.filter(id=doc_id).exists())


    def test_update_with_new_file(self):
        doc = document_create(title="V1", file=_make_file("v1.txt"), uploaded_by=self.admin)
        new_file = _make_file("v2.txt", b"new content")
        updated = document_update(document=doc, file=new_file, updated_by=self.admin)
        self.assertEqual(updated.file_name, "v2.txt")

    def test_document_str(self):
        doc = document_create(title="Report", file=_make_file("r.pdf"), uploaded_by=self.admin)
        self.assertIn("Report", str(doc))


class DocumentAPITests(TestCase):
    """Test API endpoints with RBAC."""

    def setUp(self):
        self.client = APIClient()
        self.admin = BaseUser.objects.create_user(
            username="admin_api", password="Admin@12345", role=Role.ADMIN
        )
        self.editor = BaseUser.objects.create_user(
            username="editor_api", password="Editor@12345", role=Role.EDITOR
        )
        self.viewer = BaseUser.objects.create_user(
            username="viewer_api", password="Viewer@12345", role=Role.VIEWER
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_doc(self, user=None, title="Test"):
        return document_create(
            title=title, file=_make_file(), uploaded_by=user or self.admin
        )

    # ── List ──

    def test_list_as_viewer(self):
        self._create_doc()
        self._auth(self.viewer)
        resp = self.client.get("/api/documents/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_list_unauthenticated(self):
        resp = self.client.get("/api/documents/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Create ──

    def test_create_as_editor(self):
        self._auth(self.editor)
        resp = self.client.post(
            "/api/documents/",
            {"title": "Editor Upload", "file": _make_file()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_as_admin(self):
        self._auth(self.admin)
        resp = self.client.post(
            "/api/documents/",
            {"title": "Admin Upload", "file": _make_file()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_as_viewer_forbidden(self):
        self._auth(self.viewer)
        resp = self.client.post(
            "/api/documents/",
            {"title": "Nope", "file": _make_file()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Retrieve ──

    def test_retrieve_as_viewer(self):
        doc = self._create_doc()
        self._auth(self.viewer)
        resp = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_not_found(self):
        self._auth(self.viewer)
        resp = self.client.get("/api/documents/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Update ──

    def test_update_as_editor(self):
        doc = self._create_doc()
        self._auth(self.editor)
        resp = self.client.put(
            f"/api/documents/{doc.id}/", {"title": "Updated"}, format="multipart"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "Updated")

    def test_update_as_viewer_forbidden(self):
        doc = self._create_doc()
        self._auth(self.viewer)
        resp = self.client.put(
            f"/api/documents/{doc.id}/", {"title": "Nope"}, format="multipart"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Delete ──

    def test_delete_as_admin(self):
        doc = self._create_doc()
        self._auth(self.admin)
        resp = self.client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_as_editor_forbidden(self):
        doc = self._create_doc()
        self._auth(self.editor)
        resp = self.client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_as_viewer_forbidden(self):
        doc = self._create_doc()
        self._auth(self.viewer)
        resp = self.client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Download ──

    def test_download(self):
        doc = self._create_doc()
        self._auth(self.viewer)
        resp = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", resp.get("Content-Disposition", ""))

    # ── Filter ──

    def test_filter_by_title(self):
        self._create_doc(title="Alpha Report")
        self._create_doc(title="Beta Summary")
        self._auth(self.viewer)
        resp = self.client.get("/api/documents/?title=Alpha")
        self.assertEqual(resp.data["count"], 1)

    # ── Pagination ──

    def test_pagination(self):
        for i in range(15):
            self._create_doc(title=f"Doc {i}")
        self._auth(self.viewer)
        resp = self.client.get("/api/documents/?limit=5&offset=0")
        self.assertEqual(len(resp.data["results"]), 5)
        self.assertEqual(resp.data["count"], 15)


class AdminAPITests(TestCase):
    """Test admin-only endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = BaseUser.objects.create_user(
            username="admin_mgmt", password="Admin@12345", role=Role.ADMIN
        )
        self.editor = BaseUser.objects.create_user(
            username="editor_mgmt", password="Editor@12345", role=Role.EDITOR
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_list_users(self):
        self._auth(self.admin)
        resp = self.client.get("/api/documents/admin/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_create_user(self):
        self._auth(self.admin)
        resp = self.client.post(
            "/api/documents/admin/users/",
            {"username": "newuser", "password": "NewPass@123", "role": "viewer"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_update_role(self):
        self._auth(self.admin)
        resp = self.client.patch(
            f"/api/documents/admin/users/{self.editor.id}/role/",
            {"role": "admin"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.editor.refresh_from_db()
        self.assertEqual(self.editor.role, Role.ADMIN)

    def test_editor_cannot_access_admin(self):
        self._auth(self.editor)
        resp = self.client.get("/api/documents/admin/users/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_audit_logs(self):
        self._auth(self.admin)
        resp = self.client.get("/api/documents/audit-logs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_editor_cannot_access_audit_logs(self):
        self._auth(self.editor)
        resp = self.client.get("/api/documents/audit-logs/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class RoleTests(TestCase):
    """Test role assignment."""

    def test_default_role_is_viewer(self):
        user = BaseUser.objects.create_user(username="defaultuser", password="Pass@12345")
        self.assertEqual(user.role, Role.VIEWER)

    def test_superuser_gets_admin_role(self):
        user = BaseUser.objects.create_superuser(username="superadmin", password="Pass@12345")
        self.assertEqual(user.role, Role.ADMIN)
