"""Actual native OPA/crypto observations replay without tools or source files."""
import base64
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.repository_replay import ReplayRepositoryOPA,ReplayRepositoryCrypto,ReplayRepositoryClock,crypto_input
from lib.providers.repository_opa import RepositoryOPA
from lib.providers.attestation_verification import verify,outcome
from lib.portable.runtime import approved_opa_hashes
from lib.attestation_assessment import canonical_statement
from lib.v2_boundary import violations


@unittest.skipUnless(shutil.which('opa'),'pinned OPA absent')
class RepositoryOPAReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.area=Path(self.temporary.name).resolve();self.area.chmod(0o700)
        self.hashes=frozenset(approved_opa_hashes('1.18.2'))
        self.port=RepositoryOPA(shutil.which('opa'),approved_hashes=self.hashes,workarea=self.area,
            on_intent=lambda row:None,on_start=lambda row:None,on_finish=lambda row:None)
        self.context={'tool_path':self.port.tool[0],'tool_sha256':self.port.tool[1],'workarea':str(self.area)}
        self.files={'policies/opa/fixture.rego':b'package fixture\nallow := true\n'}
        self.expected=self.port.check(self.files,directory_present=True)
        self.rows=copy.deepcopy(self.port.observations)

    def replay(self,rows=None):return ReplayRepositoryOPA(self.context,self.rows if rows is None else rows,approved_hashes=self.hashes)

    def test_complete_actual_streams_and_result_replay_without_starting_any_native_process(self):
        shutil.rmtree(self.area)
        with patch('subprocess.Popen',side_effect=AssertionError('no process during replay')):
            replay=self.replay();actual=replay.check(self.files,directory_present=True);replay.finish()
        self.assertEqual(vars(actual),vars(self.expected))

    def test_real_native_syntax_failure_is_a_complete_retained_failure_result(self):
        files={'policies/opa/broken.rego':b'package broken\ninvalid @\n'}
        expected=self.port.check(files,directory_present=True)
        replay=self.replay(copy.deepcopy([self.rows[0],self.port.observations[-1]]))
        self.assertEqual(vars(replay.check(files,directory_present=True)),vars(expected));replay.finish()
        self.assertNotEqual(expected.returncode,0)

    def test_changed_or_extra_policy_bytes_cannot_consume_the_original_observation(self):
        with self.assertRaises(ValueError):self.replay().check(self.files|{'policies/opa/extra.rego':b''},directory_present=True)
        with self.assertRaises(ValueError):self.replay().check({'policies/opa/fixture.rego':b'changed'},directory_present=True)
        with self.assertRaises(ValueError):self.replay().check(self.files,directory_present=False)

    def test_truncated_unstarted_timed_out_extra_field_and_bad_cleanup_are_not_complete(self):
        for key,value in [('process_started',False),('timed_out',True),('output_truncated',True),
                          ('error_type','OSError'),('cleanup_absence_check','unproven'),('unrecognized',True),('returncode',True)]:
            rows=copy.deepcopy(self.rows);rows[-1][key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.replay(rows).check(self.files,directory_present=True)

    def test_version_tool_hash_and_forged_argv_cannot_be_relabelled(self):
        rows=copy.deepcopy(self.rows);rows[0]['stdout_base64']=base64.b64encode(b'Version: 0.1.0\n').decode()
        with self.assertRaises(ValueError):self.replay(rows)
        rows=copy.deepcopy(self.rows);rows[-1]['tool_sha256']='0'*64
        with self.assertRaises(ValueError):self.replay(rows).check(self.files,directory_present=True)
        rows=copy.deepcopy(self.rows);rows[-1]['argv'][-1]='/outside/policies/opa'
        with self.assertRaises(ValueError):self.replay(rows).check(self.files,directory_present=True)

    def test_missing_and_unused_native_observations_remain_visible(self):
        replay=self.replay()
        with self.assertRaisesRegex(ValueError,'unused'):replay.finish()
        replay.check(self.files,directory_present=True)
        with self.assertRaisesRegex(ValueError,'missing'):replay.check(self.files,directory_present=True)

    def test_boolean_byte_count_is_not_equivalent_to_an_integer_descriptor(self):
        empty={'policies/opa/empty.rego':b''};self.port.check(empty,directory_present=True)
        rows=copy.deepcopy([self.rows[0],self.port.observations[-1]])
        rows[-1]['request']['files']['policies/opa/empty.rego']['bytes']=False
        with self.assertRaises(ValueError):self.replay(rows).check(empty,directory_present=True)


@unittest.skipUnless(shutil.which('openssl'),'native OpenSSL absent')
class RepositoryCryptoReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.area=Path(self.temporary.name).resolve();self.area.chmod(0o700)
        attestation=json.loads((ROOT/'docs/examples/evidence-attestation.example.json').read_bytes())
        registry=yaml.safe_load((ROOT/'model/evidence/evidence-trust-roots.yaml').read_bytes())
        root=next(row for row in registry['roots'] if row['key_id']==attestation['key_id'])
        self.key=root['public_key_pem'];self.statement=canonical_statement(attestation['statement'])
        self.signature=base64.b64decode(attestation['signature'],validate=True)

    def packet(self,signature=None):
        signature=self.signature if signature is None else signature
        row,stdout,stderr=verify(self.key,self.statement,signature,self.area,'legacy-attestation-pilot-v1',lambda row:None)
        return {'profile':'legacy-attestation-pilot-v1','input':crypto_input(self.key,self.statement,signature),
            'observation':row,'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode()}

    def test_actual_valid_signature_and_native_raw_observation_replay_without_openssl(self):
        packet=self.packet();expected=outcome(packet['observation'])
        self.assertTrue(expected[0])
        shutil.rmtree(self.area)
        with patch('subprocess.Popen',side_effect=AssertionError('no native crypto during replay')):
            replay=ReplayRepositoryCrypto([packet]);self.assertEqual(replay(self.key,self.statement,self.signature),expected);replay.finish()

    def test_actual_invalid_signature_keeps_the_complete_failure_reason(self):
        signature=bytes([self.signature[0]^1])+self.signature[1:]
        packet=self.packet(signature);expected=outcome(packet['observation']);self.assertFalse(expected[0])
        replay=ReplayRepositoryCrypto([packet]);self.assertEqual(replay(self.key,self.statement,signature),expected);replay.finish()

    def test_missing_native_tool_is_retained_as_unavailable_and_not_a_fake_valid_signature(self):
        with patch('shutil.which',return_value=None):packet=self.packet()
        expected=outcome(packet['observation']);self.assertFalse(expected[0])
        replay=ReplayRepositoryCrypto([packet]);self.assertEqual(replay(self.key,self.statement,self.signature),expected);replay.finish()

    def test_changed_key_statement_signature_and_outcome_are_rejected(self):
        packet=self.packet()
        for key,statement,signature in [(self.key+'changed',self.statement,self.signature),
                (self.key,self.statement+b'changed',self.signature),(self.key,self.statement,self.signature+b'changed')]:
            with self.assertRaises(ValueError):ReplayRepositoryCrypto([packet])(key,statement,signature)
        packet=copy.deepcopy(packet);packet['observation']['signature_valid']=not packet['observation']['signature_valid']
        with self.assertRaises(ValueError):ReplayRepositoryCrypto([packet])(self.key,self.statement,self.signature)

    def test_missing_unused_and_incomplete_native_crypto_observations_cannot_pass(self):
        with self.assertRaises(ValueError):ReplayRepositoryCrypto([])(self.key,self.statement,self.signature)
        replay=ReplayRepositoryCrypto([self.packet()])
        with self.assertRaises(ValueError):replay.finish()
        packet=self.packet();packet['observation']['error_type']='OSError'
        with self.assertRaises(ValueError):ReplayRepositoryCrypto([packet])(self.key,self.statement,self.signature)


class RepositoryClockReplayTests(unittest.TestCase):
    def test_actual_clock_order_and_microseconds_are_retained_without_reading_the_clock(self):
        values=['2026-11-15T12:00:00Z','2026-11-15T12:00:01.123456Z']
        replay=ReplayRepositoryClock(values)
        self.assertEqual([replay(),replay()],values);replay.finish()
        with self.assertRaises(ValueError):replay()

    def test_missing_invalid_or_unused_time_observations_fail(self):
        with self.assertRaises(ValueError):ReplayRepositoryClock(['not-time'])
        with self.assertRaises(ValueError):ReplayRepositoryClock(['2026-11-15T12:00:00Z']).finish()

    def test_replay_core_does_not_import_a_native_or_legacy_provider(self):
        name='scripts/lib/repository_replay.py';self.assertEqual(violations(name,(ROOT/name).read_text()),[])


if __name__=='__main__':unittest.main()
