"""Deterministic and safely embedded read-only lifecycle presentation."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_governance_lifecycle_overview import OUTPUT as OVERVIEW_OUTPUT, REPORT, PROFILE
from generate_governance_lifecycle_viewer import OUTPUT, generate, render_viewer, safe_json, validate_viewer
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.scripts = {}
        self.ids = []
        self.tags = []
        self.csp = ""
        self.active = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "script":
            self.active = a["id"]
            self.scripts[self.active] = ""
        if tag == "meta" and a.get("http-equiv") == "Content-Security-Policy":
            self.csp = a["content"]

    def handle_data(self, value):
        if self.active:
            self.scripts[self.active] += value

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = None


class LifecycleViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overview = strict_json((ROOT / OVERVIEW_OUTPUT).read_bytes())

    def test_checked_in_html_is_exact_verified_overview_and_has_one_app_script(self):
        html = validate_viewer()
        page = Page(html)
        self.assertEqual(json.loads(page.scripts["lifecycle-data"]), self.overview)
        self.assertEqual(set(page.scripts), {"lifecycle-data", "app"})
        self.assertEqual(len(page.ids), len(set(page.ids)))
        self.assertEqual(html, render_viewer(self.overview))

    def test_untrusted_text_roundtrips_without_creating_html_or_executable_scripts(self):
        payload = {"text": '</script><script>alert("x")</script>&<>\u2028\u2029@@SCRIPT_HASH@@'}
        encoded = safe_json(payload)
        self.assertNotIn("<", encoded)
        self.assertNotIn("&", encoded)
        page = Page('<script id="payload" type="application/json">' + encoded + '</script>')
        self.assertEqual(set(page.scripts), {"payload"})
        self.assertEqual(json.loads(page.scripts["payload"]), payload)

    def test_csp_matches_exact_script_and_denies_network_forms_and_external_assets(self):
        page = Page(render_viewer(self.overview))
        digest = base64.b64encode(hashlib.sha256(page.scripts["app"].encode()).digest()).decode()
        self.assertIn("script-src 'sha256-" + digest + "'", page.csp)
        for directive in ("default-src 'none'", "connect-src 'none'", "base-uri 'none'", "form-action 'none'"):
            self.assertIn(directive, page.csp)
        self.assertFalse(any(tag in ("form", "iframe") or "src" in attrs for tag, attrs in page.tags))
        self.assertNotIn("innerHTML", page.scripts["app"])
        self.assertNotIn("eval(", page.scripts["app"])

    def test_every_interactive_control_has_a_label_or_visible_button_text(self):
        page = Page(render_viewer(self.overview))
        labels = {attrs.get("for") for tag, attrs in page.tags if tag == "label"}
        controls = {attrs["id"] for tag, attrs in page.tags if tag in ("input", "select")}
        self.assertTrue(controls <= labels)
        self.assertEqual(controls, {"scenario", "event-type", "event-search"})
        self.assertIn("noscript", [tag for tag, attrs in page.tags])

    def test_output_cannot_overwrite_inputs_or_official_viewer_including_symlinks(self):
        paths = ("status/bad.html", PROFILE, "governance/lifecycle/bad.html", "scripts/bad.html",
                 "schemas/bad.html", "generated/viewer/status-viewer.html")
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ContractError):
                generate(output=ROOT / path)
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "official.html"
            alias.symlink_to(ROOT / "generated/viewer/status-viewer.html")
            with self.assertRaises(ContractError):
                generate(output=alias)

    def test_generation_rejects_forged_overview_before_touching_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (PROFILE, OVERVIEW_OUTPUT, REPORT):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, root / relative)
            shutil.copytree(ROOT / "governance/lifecycle", root / "governance/lifecycle")
            first = generate(root)
            self.assertEqual(first, (ROOT / OUTPUT).read_text())
            broken = strict_json((root / OVERVIEW_OUTPUT).read_bytes())
            broken["scenarios"][1]["metrics"]["current_finding_states"]["closed"] = 999
            (root / OVERVIEW_OUTPUT).write_bytes(json_bytes(broken))
            with self.assertRaisesRegex(ContractError, "overview differs"):
                generate(root)
            self.assertEqual((root / OUTPUT).read_text(), first)

    def test_validation_rejects_modified_html_even_if_embedded_data_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / OUTPUT).parent.mkdir(parents=True)
            (root / OUTPUT).write_text(render_viewer(self.overview).replace("Live acceptance is pending", "Live acceptance is granted"))
            with self.assertRaisesRegex(ContractError, "viewer differs"):
                validate_viewer(root, overview=self.overview)


if __name__ == "__main__":
    unittest.main()
