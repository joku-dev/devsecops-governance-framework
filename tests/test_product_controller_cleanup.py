"""Known Python controller cleanup must reach its own nested process group."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers.product_test_worker import supervise


class ProductControllerCleanup(unittest.TestCase):
    def test_timeout_allows_known_controller_finally_to_reap_its_inner_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            program = '\n'.join([
                'import subprocess,sys,time,os,signal',
                'from pathlib import Path',
                'p=subprocess.Popen([sys.executable,"-B","-c","import time;time.sleep(30)"],start_new_session=True)',
                'Path("inner.pid").write_text(str(p.pid))',
                'try:',
                ' time.sleep(30)',
                'finally:',
                ' os.killpg(p.pid,signal.SIGTERM)',
                ' p.wait(timeout=2)',
                ' Path("inner-reaped").write_text("reaped")',
            ])
            try:
                with self.assertRaisesRegex(TimeoutError, 'wall_budget'):
                    supervise([sys.executable, '-B', '-c', program], root,
                        {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}, root, timeout=1)
                pid = int((root / 'inner.pid').read_text())
                self.assertEqual((root / 'inner-reaped').read_text(), 'reaped')
                self.assertNotEqual(subprocess.run(['/bin/ps', '-p', str(pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode, 0)
            finally:
                # Preserve ownership even if this regression fails.
                if (root / 'inner.pid').exists():
                    pid = int((root / 'inner.pid').read_text())
                    try:
                        os.killpg(pid, 15)
                    except ProcessLookupError:
                        pass
