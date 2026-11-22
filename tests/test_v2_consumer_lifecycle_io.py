"""Original consumer ancestor checks and exact two-ledger store reconstruction."""
from pathlib import Path
import copy, hashlib, os, shutil, sys, tempfile, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from jsonschema import Draft202012Validator
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.consumer_lifecycle_io import NativeConsumerIO,native_effects
from lib.consumer_lifecycle_io import ReplayConsumerIO,replay_effects,LEDGERS,ConsumerLedgerProjection
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_ports import exclusive_factory
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_validation_budget import InputAdmissionError

def transaction_name(raw):
    import json
    t=json.loads(raw)
    return f"{t['sequence']:08d}-{t['transaction_id'].split(':')[1]}.json"

class ConsumerIO(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.parent=Path(t.name).resolve();self.source=self.parent/'source';self.source.mkdir(mode=0o700);self.serial=0
    def owner(self,mode):
        self.serial+=1;p=self.parent/f'state-{self.serial}';p.mkdir(mode=0o700);record=Record(p/'records',{'mode':mode},{'prototype':True});record.append({'kind':'execution-intent'})
        return record,NativeConsumerIO(record,mode=mode,cwd=str(self.source),private_state=p,product_root=ROOT,source=str(self.source),transaction_name=transaction_name)
    def close(self,record,owner):
        record.finish('complete',{'exit_code':0},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        def complete_archive_check():
            for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
            return closed()
        return events,lambda ref:cache[ref['sha256']],complete_archive_check
    def test_complete_all_ancestor_is_symlink_checks_include_system_owned_directories(self):
        record,owner=self.owner('private-candidate');path=self.source/'profile.json';path.write_bytes(b'{}');calls=[path,*path.parents]
        values=[owner.probe(str(p),'is_symlink',str(p)) for p in calls];self.assertEqual(values,[p.is_symlink() for p in calls]);self.assertFalse(any(values))
        events,blob,closed=self.close(record,owner);shutil.rmtree(self.source);again=ReplayConsumerIO(events,blob,'private-candidate',str(self.source),source=str(self.source),transaction_name=transaction_name)
        with patch('os.lstat',side_effect=AssertionError('No native link lookup')),patch('os.open',side_effect=AssertionError('No native input')):
            self.assertEqual([again.probe(str(p),'is_symlink',str(p)) for p in calls],values);again.finish()
        self.assertTrue(closed())
    def test_link_probe_returns_the_original_boolean_and_resealed_identity_changes_fail(self):
        record,owner=self.owner('private-candidate');target=self.source/'ordinary';target.write_bytes(b'ordinary');link=self.source/'link';link.symlink_to(target)
        self.assertTrue(owner.probe(str(link),'is_symlink',str(link)));self.assertFalse(owner.probe(str(target),'is_symlink',str(target)))
        events,blob,closed=self.close(record,owner);again=ReplayConsumerIO(events,blob,'private-candidate',str(self.source),source=str(self.source),transaction_name=transaction_name)
        self.assertTrue(again.probe(str(link),'is_symlink',str(link)));self.assertFalse(again.probe(str(target),'is_symlink',str(target)));again.finish();self.assertTrue(closed())
        from lib.consumer_lifecycle_io import link_value
        wire={'snapshot':{'kind':'directory','identity':[1,2],'mode':0o755,'uid':0},'after':{'kind':'directory','identity':[1,3],'mode':0o755,'uid':0},'failure':None}
        with self.assertRaises(IntegrityError):link_value(again,'/','/',wire)
    def test_two_real_or_private_ledgers_lock_publish_read_and_replay_in_exact_order(self):
        for mode in ('private-candidate','selected-files'):
            with self.subTest(mode=mode):
                record,owner=self.owner(mode)
                def run(io,factory):
                    paths=PreflightPaths(str(self.source),str(self.source),io,exclusive_factory);root=paths.path(self.source);ctx=RepositoryLifecycle(root,validator_class=Draft202012Validator,path_factory=paths.path);effects=factory(io,source=str(self.source),transaction_name=transaction_name);store=SyntheticLedgerStore(ctx,path_factory=paths.path,native=effects,locking=effects,temporary=effects);values=[]
                    for ledger in LEDGERS:
                        selected=root/ledger
                        with store.writer_lock(selected):
                            record={'sequence':1,'transaction_id':'transaction:'+hashlib.sha256(ledger.encode()).hexdigest(),'isolated_store_fixture':True}
                            store.publish_transaction(selected/'transactions',record)
                        values.append(store.load_transactions(selected))
                    self.assertTrue(all(row['closed'] for row in effects.descriptors.values()) if mode=='private-candidate' else all(all(row['closed'] for row in part.values()) for part in effects.descriptors.values()))
                    if hasattr(effects,'release_resources'):
                        for status in effects.release_resources():self.assertFalse(status['remaining_descriptors']);self.assertFalse(status['errors'])
                    return values
                expected=run(owner,native_effects);self.assertEqual(len(expected),2);events,blob,closed=self.close(record,owner)
                replay=ReplayConsumerIO(events,blob,mode,str(self.source),source=str(self.source),transaction_name=transaction_name)
                with patch('os.open',side_effect=AssertionError('No native store')),patch('os.link',side_effect=AssertionError('No native hardlink')):
                    self.assertEqual(run(replay,replay_effects),expected);replay.finish()
                self.assertTrue(closed())
    def test_wide_receipt_budget_is_scoped_to_each_exact_transaction_directory(self):
        raw=b'x'*(16*1024**2+1);ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};tree=ConsumerLedgerProjection(lambda _:raw,[str(self.source/name) for name in LEDGERS]);state={'kind':'file','identity':[1,2],'mode':0o600,'content':ref}
        for ledger in LEDGERS:tree.bounded_scope(str(self.source/ledger/'transactions/entry.json'),state)
        with self.assertRaises(IntegrityError):tree.bounded_scope(str(self.source/'outside.json'),state)
