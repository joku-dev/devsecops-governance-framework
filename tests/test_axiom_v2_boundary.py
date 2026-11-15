"""Architecture regression tests, including deliberate boundary violations."""
from pathlib import Path
import sys
import json
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.v2_boundary import violations, validate_boundaries


class BoundaryTests(unittest.TestCase):
    def test_actual_v2_boundaries_have_no_provider_implementation(self):
        report=validate_boundaries(ROOT)
        self.assertTrue(report['passed'],report['findings'])
        self.assertGreaterEqual(report['core_files_checked'],13)
        self.assertGreaterEqual(report['adapter_files'],8)

    def test_sdk_and_direct_http_cannot_enter_core(self):
        for source in ('import requests','from urllib.request import urlopen',
                       'from lib.providers.operations import SCM',
                       'from lib.consumer_github import Client',
                       "__import__('requests')", "subprocess.run(['curl', endpoint])"):
            with self.subTest(source=source):
                self.assertTrue(violations('core.py',source))

    def test_cli_hosts_environment_and_api_paths_are_rejected(self):
        for source in ("command=['gh','api']", "value='https://api.github.com'",
                       "value=env.get('GITHUB_RUN_ID')", "route='/repos/' + name",
                       "if provider=='gitlab': pass"):
            with self.subTest(source=source):
                self.assertTrue(violations('core.py',source))

    def test_normalized_facts_and_provider_ports_are_allowed(self):
        source='from lib.provider_ports import SCM\nvalue=context["scm"]["provider"]\n'
        self.assertEqual(violations('core.py',source),[])

    def test_relative_provider_facade_import_is_rejected(self):
        self.assertTrue(violations('scripts/lib/portable_intake/core.py','from .transport import Reader'))

    def test_transitively_imported_helper_is_not_an_unchecked_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('config','scripts/lib/providers'): (root/name).mkdir(parents=True)
            (root/'scripts/core.py').write_text('from lib.helper import run\n')
            (root/'scripts/lib/helper.py').write_text('import requests\ndef run(): pass\n')
            (root/'scripts/compose.py').write_text('# fixture composition\n')
            (root/'config/axiom-v2-boundaries.json').write_text(json.dumps({
                'schema_version':2,'core_files':['scripts/core.py'],'composition':['scripts/compose.py'],
                'adapters':'scripts/lib/providers','compatibility_facades':[],'browser_core':[],'verification':[]}))
            report=validate_boundaries(root)
            self.assertFalse(report['passed'])
            self.assertIn('scripts/lib/helper.py',report['core_closure'])
            self.assertTrue(any(row['code']=='provider_import_in_core' for row in report['findings']))

    def test_explanatory_docstrings_do_not_create_a_runtime_dependency(self):
        self.assertEqual(violations('core.py','"""Historical GitHub adapter explanation."""'),[])

    def test_checker_pattern_data_does_not_exempt_actual_network_imports(self):
        self.assertTrue(violations('checker.py','import requests',pattern_definitions=True))
