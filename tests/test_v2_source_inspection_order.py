"""Replay must bind observed legacy iteration while retaining committed source bytes."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests/acceptance'))
from lib import source_inspection_application as app
from lib import source_snapshot_proof
from lib.provider_ports import source_inspection_profile
from lib.providers import source_inspection as adapter
from v1_source_inspection_oracle import load_fixture, make_repository, git


class RetainedLegacyOrder(unittest.TestCase):
    def test_observed_sequence_requires_exact_finite_members_and_canonical_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'.github/workflows';folder.mkdir(parents=True)
            for name in ('a.yml','b.yml','ignored.txt'):(folder/name).write_text('inert fixture')
            names=['.github/workflows/a.yml','.github/workflows/b.yml']
            self.assertEqual(adapter.source_inspection_ci_paths('legacy-ci-signatures-v1',root,list(reversed(names))),list(reversed(names)))
            self.assertEqual(adapter.source_inspection_ci_paths('canonical-ci-signatures-v2',root,names),names)
            for invalid in ([],[names[0]],[names[0],names[0]],names+['../outside'],names+['/absolute'],[names[0],{}],tuple(names)):
                with self.subTest(invalid=invalid),self.assertRaises(ValueError):adapter.source_inspection_ci_paths('legacy-ci-signatures-v1',root,invalid)
            with self.assertRaisesRegex(ValueError,'source_inspection_canonical_ci_order_required'):
                adapter.source_inspection_ci_paths('canonical-ci-signatures-v2',root,list(reversed(names)))

    def test_legacy_replay_retains_first_observed_order_after_iterator_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);fixtures=ROOT/'tests/fixtures/axiom-v1-parity/source-inspection';case=load_fixture(fixtures)['cases'][0]
            repository=base/'consumer';make_repository(repository,case)
            workflow=repository/'.github/workflows/second.yml';workflow.write_text('name: Second\njobs: {}\n');git(repository,'add','--all');git(repository,'commit','-m','second CI file');revision=git(repository,'rev-parse','HEAD')
            node=base/'node';node.mkdir(mode=0o700);(node/'state').mkdir(mode=0o700)
            context=app.SourceInspectionContext(node,{'node_id':'retained-order-fixture','product':'axiom-v2'})
            original_iterator=adapter.iter_ci_files
            def ordered(root,reverse=False):return iter(sorted(original_iterator(root),key=lambda p:p.relative_to(root).as_posix().encode(),reverse=reverse))
            with patch.object(adapter,'iter_ci_files',side_effect=lambda root:ordered(root,True)):
                identifier,value=context.create('all',repository,revision,'synthetic/consumer',source_inspection_profile('legacy-ci-signatures-v1'),'2026-11-15T12:00:00Z')
            self.assertEqual(value['schema_version'],2)
            self.assertGreater(len(value['ci_iteration_paths']),1)
            saved={name:(context.artifacts/identifier/name).read_bytes() for name in value['files']}
            data,manifest=context.input_data(value['input_id']);self.assertEqual(source_snapshot_proof.verify(data,manifest),manifest);self.assertFalse(value['working_tree_used'])
            shutil.rmtree(repository)
            with patch.object(adapter,'iter_ci_files',side_effect=lambda root:ordered(root,False)):
                # A different filesystem enumeration is not a change to the captured input.
                self.assertEqual(context.inspect(identifier),value)
            self.assertEqual(saved,{name:(context.artifacts/identifier/name).read_bytes() for name in value['files']})


if __name__=='__main__':unittest.main()
