"""Durability, exact event bytes, source binding and interrupted-record detection."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.repository_journal import RepositoryJournal,read_journal


class RepositoryJournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve();self.root.chmod(0o700)
        self.header={'node_id':'controlled-node','operation_id':'controlled-operation','source_revision':'a'*40}

    def completed(self):
        with RepositoryJournal(self.root,self.header) as journal:
            journal.append({'kind':'intent','name':'first'})
            journal.append({'kind':'completed','name':'first','raw':'ä\nbytes'})
        return read_journal(self.root,expected_header=self.header)

    def test_exact_order_content_hash_chain_and_operation_binding_round_trip(self):
        rows=self.completed()
        self.assertEqual([r['sequence'] for r in rows],[1,2,3])
        self.assertIsNone(rows[0]['previous'])
        self.assertEqual(rows[1]['previous'],rows[0]['sha256'])
        self.assertEqual(rows[-1]['payload']['raw'],'ä\nbytes')
        with self.assertRaises(ValueError):read_journal(self.root,expected_header=self.header|{'node_id':'another-node'})

    def test_every_record_is_fsynced_before_append_returns(self):
        actual=os.fsync;calls=[]
        def sync(fd):calls.append(fd);return actual(fd)
        with patch('os.fsync',side_effect=sync):
            with RepositoryJournal(self.root,self.header) as journal:
                before=len(calls);journal.append({'kind':'intent'})
                self.assertGreater(len(calls),before)
                self.assertEqual(read_journal(self.root,expected_header=self.header)[-1]['payload'],{'kind':'intent'})

    def test_payload_modification_and_sequence_deletion_cannot_preserve_the_chain(self):
        rows=self.completed();path=self.root/'events.jsonl';raw=path.read_bytes()
        value=copy.deepcopy(rows);value[1]['payload']['name']='changed'
        path.write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n' for r in value))
        with self.assertRaises(ValueError):read_journal(self.root)
        path.write_bytes(raw.splitlines(keepends=True)[0]+raw.splitlines(keepends=True)[2])
        with self.assertRaises(ValueError):read_journal(self.root)

    def test_duplicate_keys_boolean_sequence_and_noncanonical_whitespace_are_rejected(self):
        self.completed();path=self.root/'events.jsonl';raw=path.read_bytes()
        variants=[raw.replace(b'"sequence":1',b'"sequence":true',1),
                  raw.replace(b'"sequence":1',b'"sequence":1,"sequence":1',1),
                  raw.replace(b'"sequence":1',b'"sequence": 1',1)]
        for value in variants:
            path.write_bytes(value)
            with self.assertRaises(ValueError):read_journal(self.root)

    def test_truncated_tail_and_empty_or_unbound_journal_are_not_completed_operations(self):
        self.completed();path=self.root/'events.jsonl';raw=path.read_bytes();path.write_bytes(raw+b'{')
        with self.assertRaises(ValueError):read_journal(self.root)
        path.write_bytes(b'')
        with self.assertRaises(ValueError):read_journal(self.root)

    def test_existing_journal_is_never_overwritten_or_resumed(self):
        self.completed();before=(self.root/'events.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):RepositoryJournal(self.root,self.header)
        self.assertEqual((self.root/'events.jsonl').read_bytes(),before)

    def test_hardlink_symlink_and_shared_mode_journals_are_not_private_records(self):
        self.completed();path=self.root/'events.jsonl'
        path.chmod(0o644)
        with self.assertRaises(ValueError):read_journal(self.root)
        path.chmod(0o600);link=self.root/'linked';os.link(path,link)
        with self.assertRaises(ValueError):read_journal(self.root)
        link.unlink();path.rename(self.root/'saved');path.symlink_to(self.root/'saved')
        with self.assertRaises((ValueError,OSError)):read_journal(self.root)

    def test_live_file_replacement_is_detected_before_any_further_write(self):
        with RepositoryJournal(self.root,self.header) as journal:
            path=self.root/'events.jsonl';path.rename(self.root/'original')
            path.write_bytes(b'foreign file');path.chmod(0o600)
            with self.assertRaises(ValueError):journal.append({'kind':'must not append'})
            self.assertEqual(path.read_bytes(),b'foreign file')

    def test_live_root_replacement_is_detected_before_writing_the_replacement(self):
        with RepositoryJournal(self.root,self.header) as journal:
            previous=self.root.with_name(self.root.name+'-owned-old');self.root.rename(previous)
            import shutil
            self.addCleanup(shutil.rmtree,previous);self.root.mkdir(mode=0o700)
            with self.assertRaises(ValueError):journal.append({'kind':'must not append'})
            self.assertEqual(list(self.root.iterdir()),[])

    def test_disk_sync_failure_poisoning_prevents_a_later_successful_append(self):
        with RepositoryJournal(self.root,self.header) as journal:
            with patch('os.fsync',side_effect=OSError('controlled disk failure')):
                with self.assertRaises(OSError):journal.append({'kind':'native intent'})
            with self.assertRaisesRegex(ValueError,'not_appendable'):journal.append({'kind':'later'})

    def test_partial_os_write_failure_leaves_an_incomplete_tail_and_cannot_resume(self):
        with RepositoryJournal(self.root,self.header) as journal:
            actual=os.write;count=0
            def write(fd,raw):
                nonlocal count
                count+=1
                if count==1:return actual(fd,raw[:7])
                raise OSError('controlled partial write')
            with patch('os.write',side_effect=write):
                with self.assertRaises(OSError):journal.append({'kind':'intent'})
            with self.assertRaises(ValueError):journal.append({'kind':'later'})
        with self.assertRaises(ValueError):read_journal(self.root)

    def test_nonfinite_values_and_event_budget_cannot_write_invalid_json(self):
        with RepositoryJournal(self.root,self.header) as journal:
            before=(self.root/'events.jsonl').read_bytes()
            with self.assertRaises(ValueError):journal.append({'value':float('nan')})
            with patch('lib.providers.repository_journal.MAX_EVENT',400):
                with self.assertRaises(ValueError):journal.append({'data':'x'*1000})
            self.assertEqual((self.root/'events.jsonl').read_bytes(),before)
            journal.append({'kind':'still valid because no invalid bytes were written'})

    def test_all_descriptors_close_even_if_header_creation_fails(self):
        actual_open,actual_close=os.open,os.close;owned=set()
        def opened(*args,**kwargs):
            fd=actual_open(*args,**kwargs);owned.add(fd);return fd
        def closed(fd):owned.discard(fd);return actual_close(fd)
        with patch('os.open',side_effect=opened),patch('os.close',side_effect=closed):
            with self.assertRaises(ValueError):RepositoryJournal(self.root,{'bad':float('inf')})
        self.assertEqual(owned,set())

    def test_private_root_is_required_and_closed_instances_are_not_appendable(self):
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):RepositoryJournal(self.root,self.header)
        self.root.chmod(0o700)
        journal=RepositoryJournal(self.root,self.header);journal.close();journal.close()
        with self.assertRaises(ValueError):journal.append({'kind':'after close'})


if __name__=='__main__':unittest.main()
