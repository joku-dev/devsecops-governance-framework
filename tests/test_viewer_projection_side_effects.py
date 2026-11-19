"""The shared complete data projection must not write Viewer output files."""
from pathlib import Path
import hashlib
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.viewer_app import project_data


class ReadOnlyViewerProjection(unittest.TestCase):
    def test_complete_projection_preserves_all_existing_output_bytes_and_members(self):
        folder = ROOT / 'generated/viewer/app'
        def snapshot():
            return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in folder.rglob('*') if p.is_file()}
        before = snapshot()
        data = project_data(ROOT)
        self.assertEqual(snapshot(), before)
        self.assertEqual(data['version'], 1)
        self.assertTrue(data['repositories'])
        self.assertIn('technical', data)
        self.assertIn('requirement_journeys', data)
        self.assertIn('governance_requirement_lifecycle', data)
