"""Whole previous installer outcomes and a genuinely dependency-free CLI start."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict, replace
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import install_validation_opa as current
from lib.functional_parity import git_read, V1_REFERENCE
from lib.providers import opa_bootstrap as provider

PAYLOAD=b'#!/bin/sh\nprintf "Version: 1.18.2\\n"\n'


def pinned_native_fixture(destination, cache, *, candidate=None, fetch=current.download):
    """Select only the approved asset; a different PATH build is not its fixture.

    Prepared/offline packages already expose that exact asset. A development
    environment that supplies another build acquires the approved public asset
    through the real bounded verified installer into this private test location.
    No system executable or validation environment is changed.
    """
    tool=current.select_tool()
    found=candidate if candidate is not None else shutil.which('opa')
    if found and current.matches(Path(found),tool.sha256):
        return Path(found)
    current.install(tool,destination,cache,fetch=fetch,attempts=2,timeout=60)
    if not current.matches(destination,tool.sha256):
        raise AssertionError('Approved pinned native fixture was not acquired')
    return destination


class OPABootstrapProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ModuleType('unchanged_previous_opa_bootstrap')
        cls.original.__file__=str(ROOT/'scripts/install_validation_opa.py')
        sys.modules[cls.original.__name__]=cls.original
        raw=git_read(ROOT,'show',V1_REFERENCE+':scripts/install_validation_opa.py')
        matrix=json.loads((ROOT/'config/axiom-v2-functional-parity.json').read_bytes())
        expected=next(r['v1_sha256'] for r in matrix['entrypoints']
                      if r['v1_path']=='scripts/install_validation_opa.py')
        if hashlib.sha256(raw).hexdigest()!=expected:
            raise AssertionError('Immutable original OPA installer mismatch')
        exec(compile(raw,cls.original.__file__,'exec'),cls.original.__dict__)
        cls.original_source=raw

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop(cls.original.__name__,None)

    def test_every_original_platform_pin_cache_key_and_location_order_is_preserved(self):
        for system,machine in [('Linux','x86_64'),('Linux','aarch64'),('Linux','arm64'),
                               ('Darwin','arm64'),('Darwin','x86_64')]:
            old=self.original.select_tool(system=system,machine=machine)
            new=current.select_tool(system=system,machine=machine)
            self.assertEqual(asdict(old),asdict(new))
            self.assertEqual(old.cache_key,new.cache_key)
            for mirror in ('','https://mirror.example/opa'):
                self.assertEqual(self.original.locations(old,mirror),current.locations(new,mirror))

    def compare(self, case):
        observed=[]
        for module in (self.original,current):
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);destination=root/'bin/opa';cache=root/'cache'
                tool=module.Tool('1.18.2','opa_linux_amd64_static',hashlib.sha256(PAYLOAD).hexdigest(),464348303)
                raw=PAYLOAD
                if case=='wrong-version':
                    raw=b'#!/bin/sh\nprintf "Version: 9.0.0\\n"\n'
                    tool=replace(tool,sha256=hashlib.sha256(raw).hexdigest())
                cached=cache/tool.cache_key/'opa'
                if case=='installed':
                    destination.parent.mkdir();destination.write_bytes(raw);destination.chmod(0o755)
                if case in ('cached','poisoned','cache-symlink'):
                    cached.parent.mkdir(parents=True)
                    if case=='cache-symlink':
                        target=root/'outside';target.write_bytes(raw);cached.symlink_to(target)
                    else:cached.write_bytes(b'poison' if case=='poisoned' else raw)
                if case=='fail-preserve':
                    destination.parent.mkdir();destination.write_bytes(b'previous destination')
                calls=[]
                def fetch(url,path,**options):
                    calls.append((url,options))
                    if case=='fail-preserve':raise OSError('declared unavailable')
                    if case=='fallback' and not options['api']:raise OSError('declared retry')
                    path.write_bytes(b'corrupt mirror response' if case=='mirror' and url.startswith('https://mirror.example/') else raw)
                output,error=io.StringIO(),io.StringIO();result=None;failure=None
                copier=module.install_copy
                def copy(source,target,selected):
                    if case=='cache-write-error' and cache in target.parents:raise OSError('declared cache read-only')
                    return copier(source,target,selected)
                with redirect_stdout(output),redirect_stderr(error),patch.object(module,'install_copy',side_effect=copy):
                    try:result=module.install(tool,destination,cache,fetch=fetch,sleep=lambda _:None,
                        attempts=2,timeout=17,offline=case in ('cached','poisoned','cache-symlink'),
                        mirror='https://mirror.example/opa' if case=='mirror' else '')
                    except Exception as caught:failure=(type(caught).__name__,str(caught))
                files={}
                for path in root.rglob('*'):
                    name=path.relative_to(root).as_posix()
                    if path.is_symlink():files[name]={'symlink':Path(os.readlink(path)).relative_to(root).as_posix()}
                    elif path.is_file():files[name]={'bytes':path.read_bytes(),'mode':path.stat().st_mode&0o777}
                observed.append((result,failure,output.getvalue(),error.getvalue(),files,calls))
        self.assertEqual(observed[0],observed[1],case)

    def test_whole_previous_install_outcomes_diagnostics_and_effects_remain_identical(self):
        for case in ('download','installed','cached','poisoned','cache-symlink','fail-preserve',
                     'wrong-version','fallback','mirror','cache-write-error'):
            with self.subTest(case=case):self.compare(case)

    def command(self, arguments):
        script=ROOT/'scripts/install_validation_opa.py'
        code=('import runpy,sys;sys.path.insert(0,'+repr(str(ROOT/'scripts'))+');'
              'sys.argv='+repr([str(script),*arguments])+';runpy.run_path(sys.argv[0],run_name="__main__")')
        return [sys.executable,'-I','-S','-B','-c',code]

    def test_fresh_stdlib_only_cli_describe_and_help_need_no_installed_dependencies(self):
        for args in (['--describe'],['--help']):
            result=subprocess.run(self.command(args),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            if args==['--describe']:
                tool=current.select_tool()
                self.assertEqual(result.stdout,f'cache_key={tool.cache_key}\nversion={tool.version}\nasset={tool.asset}\n')

    def test_stdlib_only_cli_offline_installs_then_repairs_from_exact_pinned_cached_binary(self):
        tool=current.select_tool()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);destination=root/'environment/bin/opa';cache=root/'cache'
            executable=pinned_native_fixture(root/'fixture/opa',root/'fixture-cache')
            self.assertEqual(hashlib.sha256(executable.read_bytes()).hexdigest(),tool.sha256)
            source=cache/tool.cache_key/'opa';source.parent.mkdir(parents=True);shutil.copyfile(executable,source)
            args=['--destination',str(destination),'--cache',str(cache),'--offline']
            for before in (None,b'corrupt existing binary',b''):
                if before is not None:destination.write_bytes(before)
                result=subprocess.run(self.command(args),capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(),tool.sha256)
                self.assertTrue(os.access(destination,os.X_OK))
            self.assertEqual(list(destination.parent.glob('.opa-*')),[])

    def test_another_path_build_is_never_executed_or_accepted_as_the_pinned_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);marker=root/'unapproved-executed'
            wrong=root/'other-opa-build'
            wrong.write_text('#!/bin/sh\ntouch '+str(marker)+'\n');wrong.chmod(0o755)
            tool=current.Tool('1.18.2','explicit-synthetic-fixture',hashlib.sha256(PAYLOAD).hexdigest(),464348303)
            cache=root/'verified-cache';held=cache/tool.cache_key/'opa';held.parent.mkdir(parents=True);held.write_bytes(PAYLOAD)
            def forbidden(*args,**kwargs):
                raise AssertionError('Verified cached fixture must not download')
            with patch.object(current,'select_tool',return_value=tool):
                result=pinned_native_fixture(root/'fixture/opa',cache,candidate=str(wrong),fetch=forbidden)
            self.assertEqual(result.read_bytes(),PAYLOAD)
            self.assertEqual(hashlib.sha256(result.read_bytes()).hexdigest(),tool.sha256)
            self.assertFalse(marker.exists())
            self.assertNotEqual(wrong.read_bytes(),PAYLOAD)

    def test_active_facade_has_no_provider_endpoints_or_direct_provider_imports(self):
        from lib.v2_boundary import violations,validate_boundaries
        source=(ROOT/'scripts/install_validation_opa.py').read_text()
        self.assertEqual(violations('scripts/install_validation_opa.py',source),[])
        self.assertNotIn('https://',source)
        self.assertNotIn('X-GitHub',source)
        self.assertTrue(validate_boundaries(ROOT)['passed'])
        self.assertEqual(current.Tool,provider.Tool)
