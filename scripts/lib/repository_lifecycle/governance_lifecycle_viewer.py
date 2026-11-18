"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
import base64
import hashlib
import json
import re
_OMITTED = object()
OUTPUT = 'generated/viewer/governance-lifecycle-viewer.html'

class LifecycleViewer:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.OUTPUT = OUTPUT
        self.input_template = self.root / 'scripts/templates/governance-lifecycle-viewer.html'

    def safe_json(self, value):
        """Preserve exact JSON values while preventing HTML script-element termination."""
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        for char, escaped in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'), ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
            payload = payload.replace(char, escaped)
        return payload

    def render_viewer(self, overview):
        self.context.contracts.schema_validator('overview').validate(overview)
        template = self.input_template.read_text(encoding='utf-8')
        self.context.contracts.require(template.count('@@DATA@@') == template.count('@@SCRIPT_HASH@@') == 1, 'Invalid viewer template placeholders')
        scripts = re.findall('<script id="app">(.*?)</script>', template, re.S)
        self.context.contracts.require(len(scripts) == 1, 'Viewer must contain one fixed executable script')
        digest = base64.b64encode(hashlib.sha256(scripts[0].encode('utf-8')).digest()).decode('ascii')
        return template.replace('@@SCRIPT_HASH@@', digest).replace('@@DATA@@', self.safe_json(overview))

    def validate_viewer(self, repo=_OMITTED, *, overview=None):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        if overview is None:
            overview = self.context.governance_lifecycle_overview.validate_overview(root)
        expected = self.render_viewer(overview)
        self.context.contracts.require((root / OUTPUT).read_text(encoding='utf-8') == expected, 'Lifecycle viewer differs from verified overview')
        return expected
