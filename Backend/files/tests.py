import io
import os
import shutil
import tempfile
import zipfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import StoredFile
from .signing import make_token, read_token
from .validators import validate_upload

User = get_user_model()

PDF = b"%PDF-1.7\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def docx_bytes(include_document=True):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        if include_document:
            archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


class ValidatorTests(SimpleTestCase):
    def test_accepts_real_files(self):
        self.assertEqual(validate_upload(SimpleUploadedFile("cv.pdf", PDF))[0], "pdf")
        self.assertEqual(validate_upload(SimpleUploadedFile("me.PNG", PNG))[0], "png")
        self.assertEqual(validate_upload(SimpleUploadedFile("cv.docx", docx_bytes()))[0], "docx")

    def test_rejects_renamed_files(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_upload(SimpleUploadedFile("cv.pdf", b"<html><script>alert(1)</script></html>"))
        self.assertEqual(ctx.exception.code, "content")

    def test_rejects_zip_pretending_to_be_docx(self):
        with self.assertRaises(ValidationError):
            validate_upload(SimpleUploadedFile("cv.docx", docx_bytes(include_document=False)))

    def test_rejects_disallowed_types(self):
        for name in ("run.exe", "page.html", "script.js", "noextension"):
            with self.assertRaises(ValidationError, msg=name) as ctx:
                validate_upload(SimpleUploadedFile(name, PDF))
            self.assertEqual(ctx.exception.code, "type")

    def test_rejects_empty_and_oversized(self):
        with self.assertRaises(ValidationError):
            validate_upload(SimpleUploadedFile("cv.pdf", b""))
        with override_settings(FILE_UPLOAD_MAX_BYTES=10):
            with self.assertRaises(ValidationError) as ctx:
                validate_upload(SimpleUploadedFile("cv.pdf", PDF))
        self.assertEqual(ctx.exception.code, "too_large")


class FileApiTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        field = StoredFile._meta.get_field("file")
        patcher = mock.patch.object(field, "storage", FileSystemStorage(location=self.media))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.alice = User.objects.create_user("alice", password="unused-test-password")
        self.bob = User.objects.create_user("bob", password="unused-test-password")

    def upload(self, user, name="cv.pdf", content=PDF):
        self.client.force_login(user)
        return self.client.post("/api/files/", {"file": SimpleUploadedFile(name, content)})

    def test_upload_returns_details_and_link(self):
        response = self.upload(self.alice)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["name"], "cv.pdf")
        self.assertEqual(body["content_type"], "application/pdf")
        self.assertEqual(body["size"], len(PDF))
        self.assertIn("/api/files/download/", body["download_url"])

        stored = StoredFile.objects.get()
        self.assertNotIn("cv", stored.file.name)  # random name on disk
        self.assertEqual(len(stored.sha256), 64)

    def test_upload_requires_login(self):
        response = self.client.post("/api/files/", {"file": SimpleUploadedFile("cv.pdf", PDF)})

        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(StoredFile.objects.count(), 0)

    def test_bad_upload_is_rejected_and_nothing_saved(self):
        response = self.upload(self.alice, "cv.pdf", b"MZ\x90\x00 not a pdf")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "content")
        self.assertEqual(StoredFile.objects.count(), 0)

    def test_owner_can_download(self):
        url = self.upload(self.alice).json()["download_url"]

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", response["Cache-Control"])

    def test_link_does_not_work_for_another_user(self):
        url = self.upload(self.alice).json()["download_url"]

        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_tampered_link_is_rejected(self):
        url = self.upload(self.alice).json()["download_url"]

        self.assertEqual(self.client.get(url.rstrip("/") + "x/").status_code, 404)

    def test_expired_link_returns_410(self):
        url = self.upload(self.alice).json()["download_url"]

        with override_settings(FILE_LINK_MAX_AGE=-1):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 410)

    def test_other_users_cannot_see_or_delete_a_file(self):
        file_id = self.upload(self.alice).json()["id"]

        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(f"/api/files/{file_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/files/{file_id}/").status_code, 404)
        self.assertEqual(StoredFile.objects.count(), 1)

    def test_owner_gets_fresh_link_and_can_delete(self):
        file_id = self.upload(self.alice).json()["id"]
        stored = StoredFile.objects.get()
        path = stored.file.path

        detail = self.client.get(f"/api/files/{file_id}/")
        self.assertEqual(detail.status_code, 200)

        self.assertEqual(self.client.delete(f"/api/files/{file_id}/").status_code, 204)
        self.assertEqual(StoredFile.objects.count(), 0)
        self.assertFalse(os.path.exists(path))

    def test_staff_can_open_any_file(self):
        stored_id = self.upload(self.alice).json()["id"]
        staff = User.objects.create_user("mentor", password="unused-test-password", is_staff=True)
        self.client.force_login(staff)

        url = self.client.get(f"/api/files/{stored_id}/").json()["download_url"]

        self.assertEqual(self.client.get(url).status_code, 200)


class SigningTests(TestCase):
    def test_token_round_trip(self):
        user = User.objects.create_user("x", password="unused-test-password")
        stored = StoredFile(owner=user)

        file_id, user_id = read_token(make_token(stored, user))

        self.assertEqual((file_id, user_id), (str(stored.pk), user.pk))

    def test_bad_token(self):
        with self.assertRaises(signing.BadSignature):
            read_token("not-a-token")
