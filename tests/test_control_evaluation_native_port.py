"""Complete actual native-port control output must retain both whole V1 wires."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import control_evaluation as controls
from lib.functional_parity import git_read
from lib.providers.compliance_opa import ComplianceOPA


class ControlEvaluationNativePort(unittest.TestCase):
    def test_all46_controls_and_whole_json_markdown_equal_original_with_actual_pinned_opa(self):
        fixtures = ROOT / 'tests/fixtures/axiom-v1-parity'
        manifest = json.loads((fixtures / 'manifest.json').read_bytes())
        for key in ('green', 'red'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                row = next(r for r in manifest['cases'] if r['id'] == 'controls-' + key)
                source = ROOT / row['input']; raw = source.read_bytes()
                expected_raw = (fixtures / row['report']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row['input_sha256'])
                self.assertEqual(hashlib.sha256(expected_raw).hexdigest(), row['report_sha256'])
                expected = json.loads(expected_raw)
                opa = ComplianceOPA(tool=shutil.which('opa'),
                    source_revision=git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
                    display_root=ROOT, input_label=source, input_bytes=raw,
                    workarea=Path(temporary).resolve() / 'opa', on_event=lambda row: None)
                observed = controls.generate_control_evaluation_report(source, native_run=opa.run)
                self.assertEqual((json.dumps(observed, indent=2)+'\n').encode(), expected_raw)
                self.assertEqual(controls.render_control_evaluation_markdown(observed),
                    controls.render_control_evaluation_markdown(expected))
                self.assertEqual(len(observed['controls']), 46)
                self.assertEqual(len(opa.observations), 11)

    def test_existing_default_callback_shape_is_preserved_without_new_keyword_arguments(self):
        with patch.object(controls, 'load_json', return_value={}), \
                patch.object(controls, 'load_controls', return_value=[]), \
                patch.object(controls, 'evaluate_policies', side_effect=lambda path: {}) as called:
            result = controls.generate_control_evaluation_report(ROOT / 'input.json')
        called.assert_called_once_with(ROOT / 'input.json')
        self.assertEqual(result['summary']['total_controls'], 0)
