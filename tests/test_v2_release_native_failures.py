"""Actual bounded-process failures remain failures and clean only owned work."""
from pathlib import Path
import os
import shlex
import shutil
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.release_verification import ReleaseVerificationEnvironment


class NativeFailureTests(unittest.TestCase):
    def run_fixture(self,body,*,timeout):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary).resolve();root=base/'source';root.mkdir(mode=0o700)
            area=base/'private';area.mkdir(mode=0o700)
            tool=base/'fixture-git';tool.write_text('#!/bin/sh\n'+body+'\n');tool.chmod(0o700)
            facts={'schema_version':1,'source_head':'1'*40,'source_tree':'2'*40,'object_format':'sha1','refs':{},'objects':{}}
            events=[];started=time.monotonic()
            with self.assertRaises((TimeoutError,ValueError)) as error:
                with ReleaseVerificationEnvironment(root,{},facts,area,git_tool=tool,on_start=events.append,timeout=timeout):
                    self.fail('A failed native capsule must not become an admitted environment')
            self.assertTrue(events);self.assertTrue(events[0]['process_started'])
            self.assertEqual(list(area.iterdir()),[]);self.assertLess(time.monotonic()-started,4)
            return str(error.exception)

    def test_actual_timeout_stops_and_removes_the_owned_capsule(self):
        self.assertIn('timeout',self.run_fixture('/bin/sleep 5',timeout=1))

    def test_actual_output_budget_never_returns_a_fake_success(self):
        head=shutil.which('head');self.assertIsNotNone(head)
        self.assertIn('output_budget',self.run_fixture(shlex.quote(head)+' -c 200000 /dev/zero',timeout=3))
