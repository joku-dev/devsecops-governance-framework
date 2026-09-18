from email.message import Message
from pathlib import Path
import io
import stat
import tempfile
import unittest
import zipfile

from urllib.request import Request

from scripts.lib.safe_archive import safe_extract_zip
from scripts.lib.secure_http import SafeHTTPSRedirectHandler, require_https


class SafeArchiveTests(unittest.TestCase):
    def archive(self, root: Path, entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> Path:
        path = root / "artifact.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries:
                archive.writestr(name, content)
        return path

    def test_extracts_regular_nested_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = self.archive(root, [("governance/report.json", b"{}")])
            output = root / "output"
            safe_extract_zip(archive, output)
            self.assertEqual((output / "governance/report.json").read_bytes(), b"{}")

    def test_rejects_traversal_absolute_windows_and_duplicate_targets(self):
        cases = [
            [("../escape", b"bad")],
            [("/absolute", b"bad")],
            [("C:\\escape", b"bad")],
            [("report.json", b"one"), ("REPORT.JSON", b"two")],
        ]
        for entries in cases:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = self.archive(root, entries)
                with self.assertRaises(ValueError):
                    safe_extract_zip(archive, root / "output")
                self.assertFalse((root / "escape").exists())

    def test_rejects_symlink_and_resource_limit_violations(self):
        symlink = zipfile.ZipInfo("link")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        cases = [
            ([(symlink, b"target")], {}),
            ([("one", b"1"), ("two", b"2")], {"max_members": 1}),
            ([("large", b"12345")], {"max_member_bytes": 4}),
            ([("one", b"123"), ("two", b"456")], {"max_total_bytes": 5}),
        ]
        for entries, limits in cases:
            with self.subTest(limits=limits), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = self.archive(root, entries)
                with self.assertRaises(ValueError):
                    safe_extract_zip(archive, root / "output", **limits)


class SafeHTTPTests(unittest.TestCase):
    def redirect(self, source: str, target: str, authorization: str = "Bearer secret") -> Request:
        request = Request(source, headers={"Authorization": authorization})
        return SafeHTTPSRedirectHandler().redirect_request(
            request,
            io.BytesIO(),
            302,
            "Found",
            Message(),
            target,
        )

    def test_requires_https_without_embedded_credentials(self):
        for url in ("http://api.github.com/data", "file:///tmp/data", "https://user@example.com/data"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_https(url)
        require_https("https://api.github.com/data")

    def test_cross_origin_redirect_strips_authorization(self):
        redirected = self.redirect("https://api.github.com/data", "https://signed.example.test/blob")
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_same_origin_redirect_keeps_authorization(self):
        redirected = self.redirect("https://api.github.com/data", "https://api.github.com/other")
        self.assertEqual(redirected.get_header("Authorization"), "Bearer secret")

    def test_https_downgrade_redirect_is_rejected(self):
        with self.assertRaises(ValueError):
            self.redirect("https://api.github.com/data", "http://api.github.com/other")


if __name__ == "__main__":
    unittest.main()
