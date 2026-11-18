"""Actual local Git capture and strict inert release-object reconstruction."""
from pathlib import Path
import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import release_reference_facts as facts
from lib.providers.release_references import ReleaseReferences


class ReferenceFactsTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)/'source';self.root.mkdir()
        self.git('init','--template=','-b','main')
        self.git('config','user.name','Local release reference test')
        self.git('config','user.email','release-reference@example.invalid')
        self.git('config','commit.gpgsign','false');self.git('config','tag.gpgsign','false')
        (self.root/'data').write_text('inert product data\n')
        self.git('add','data');self.git('commit','-qm','Product data')
        self.git('tag','-a','original-baseline-v1','-m','Original release')
        self.git('tag','lightweight-baseline-v1')
        self.git('tag','-a','nested/team-baseline-v2','-m','Nested release')
        self.git('tag','-a','chained-baseline-v2','original-baseline-v1','-m','Chained release')
        self.git('tag','v1-public-adoption');self.git('tag','unrelated-reference')
        self.provider=ReleaseReferences(self.root)

    def git(self,*args):
        env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0')
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',*args],cwd=self.root,env=env,stderr=subprocess.PIPE).decode().strip()

    def capture(self):
        before=self.git('show-ref');value=self.provider.capture();self.assertEqual(before,self.git('show-ref'))
        self.assertEqual(self.git('status','--porcelain'),'');return value

    def test_complete_original_patterns_include_nested_lightweight_and_chained_tags(self):
        value=self.capture();self.assertEqual(len(value['refs']),5)
        self.assertNotIn('unrelated-reference',value['refs'])
        expected=sorted(set(self.git('tag','--list','*baseline*').splitlines()+self.git('tag','--list','v*-public-adoption').splitlines()))
        self.assertEqual(sorted(value['refs']),expected)
        raw=facts.validate(value)
        for oid,(kind,data) in raw.items():
            self.assertEqual(self.git('cat-file','-t',oid),kind)
            self.assertEqual(facts.digest(kind,data,value['object_format']),oid)
        self.assertEqual(value['source_head'],self.git('rev-parse','HEAD'))
        self.assertEqual(value['source_tree'],self.git('rev-parse','HEAD^{tree}'))

    def test_complete_original_blob_and_tree_targets_are_retained_for_native_failure_semantics(self):
        blob=self.git('rev-parse','HEAD:data');tree=self.git('rev-parse','HEAD^{tree}')
        self.git('tag','blob-baseline-v1',blob);self.git('tag','tree-baseline-v1',tree)
        value=self.capture();objects=facts.validate(value)
        self.assertEqual(objects[blob][0],'blob');self.assertEqual(objects[tree][0],'tree')

    def test_offline_validation_uses_only_retained_bytes_after_caller_removal(self):
        value=self.capture();self.root.rename(self.root.with_name('removed-caller'))
        with patch('lib.review_git.git',side_effect=AssertionError('native access forbidden')):
            objects=facts.validate(value)
        self.assertTrue(objects)

    def test_closed_fields_types_formats_names_hashes_and_encoding_reject_tampering(self):
        original=self.capture();oid=next(iter(original['objects']))
        changes=[lambda v:v.update(untrusted_authority=True),lambda v:v.update(schema_version=True),
            lambda v:v.update(object_format=['sha1']),lambda v:v.update(source_head='0'*7),
            lambda v:v['refs'].update({'../escape-baseline':oid}),lambda v:v['refs'].update({'unrelated-name':oid}),
            lambda v:v['objects'][oid].update(extra=False),lambda v:v['objects'][oid].update(sha256='0'*64),
            lambda v:v['objects'][oid].update(base64='not-base64!'),lambda v:v['objects'][oid].update(kind='executable')]
        for change in changes:
            with self.subTest(change=change):
                value=copy.deepcopy(original);change(value)
                with self.assertRaises(ValueError):facts.validate(value)

    def test_missing_target_and_unrelated_objects_are_not_silently_dropped(self):
        original=self.capture();value=copy.deepcopy(original)
        chained=value['refs']['chained-baseline-v2'];target,_=facts.tag_target(base64.b64decode(value['objects'][chained]['base64']),value['object_format'])
        del value['objects'][target]
        with self.assertRaises(ValueError):facts.validate(value)
        raw=b'unreferenced data';oid=facts.digest('blob',raw,original['object_format'])
        original['objects'][oid]={'kind':'blob','base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
        with self.assertRaisesRegex(ValueError,'unexpected_release_reference_object'):facts.validate(original)

    def test_count_byte_and_chain_limits_are_explicit_guards(self):
        value=self.capture()
        for name,limit in [('MAX_REFS',1),('MAX_OBJECTS',1),('MAX_OBJECT',1),('MAX_TOTAL',1),('MAX_CHAIN',1)]:
            with self.subTest(limit=name),patch.object(facts,name,limit):
                with self.assertRaises(ValueError):facts.validate(value)

    def test_reference_change_during_capture_is_rejected(self):
        original=self.provider.refs;calls=[]
        def changed():
            calls.append(True)
            if len(calls)==2:self.git('tag','late-baseline-v3')
            return original()
        with patch.object(self.provider,'refs',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed_during_capture'):self.provider.capture()

    def test_commit_ancestors_and_trees_are_not_imported_as_hidden_history(self):
        value=self.capture();objects=facts.validate(value)
        self.assertNotIn(value['source_tree'],objects)
        self.assertEqual(sum(kind=='commit' for kind,raw in objects.values()),1)
        self.assertTrue(all(kind in ('tag','commit') for kind,raw in objects.values()))


class Sha256ReferenceFactsTests(ReferenceFactsTests):
    def git(self,*args):
        if args and args[0]=='init':args=('init','--object-format=sha256',*args[1:])
        return super().git(*args)


if __name__=='__main__':unittest.main()
