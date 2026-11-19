"""Whole standalone validator outcomes versus its immutable original source."""
from pathlib import Path
import hashlib,importlib.util,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.provenance_validation import ProvenanceValidation
from lib.validation_files import ValidationFiles

class StandaloneProvenance(unittest.TestCase):
    def original(self,root):
        path=ROOT/'tests/fixtures/v2-repository-validation/validate_evidence_agent_provenance.py.txt'
        # Immutable6b557fe bytes, also available in a sparse installed product.
        # The retired source entrypoint is intentionally not a physical file.
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'d13651b2e524f47e76f5d54e7274c580802beeda93b9f2969b1ec30b0b5c126a')
        from importlib.machinery import SourceFileLoader
        loader=SourceFileLoader('unchanged_provenance_reference',str(path));spec=importlib.util.spec_from_loader(loader.name,loader);value=importlib.util.module_from_spec(spec);loader.exec_module(value)
        value.ROOT=root;value.SCHEMA_PATH=root/'schemas/evidence-agent-provenance.schema.json';return value
    def compare(self,record,*,source=b'{"subjects":[{"id":"one","digest":"expected"}]}',name='case.json'):
        schema=b'{"type":"object","properties":{"evidence":{"type":"object"}}}'
        files={'schemas/evidence-agent-provenance.schema.json':schema,'status/evidence-agent-provenance/'+name:record}
        if source is not None:files['evidence.json']=source
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            for relative,raw in files.items():
                p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            original=self.original(root)
            try:errors=original.validate_records(root/'status/evidence-agent-provenance')
            except Exception as error:
                with self.assertRaises(type(error)):ProvenanceValidation(ValidationFiles(files,label=str(root))).run()
                return
            value=ProvenanceValidation(ValidationFiles(files,label=str(root))).run()
            expected={'returncode':1 if errors else 0,'stdout':'' if errors else 'Evidence agent provenance validation passed\n','stderr':('Evidence agent provenance validation failed\n'+'\n'.join(errors)+'\n') if errors else ''}
            self.assertEqual(value,expected)
    def test_valid_missing_and_mismatched_subjects_and_optional_evidence(self):
        for subject,digest,source in (('one','expected',b'{"subjects":[{"id":"one","digest":"expected"}]}'),('missing','expected',b'{}'),('one','changed',b'{"subjects":[{"id":"one","digest":"expected"}]}'),('one','expected',None)):
            with self.subTest(subject=subject,digest=digest,source=source):self.compare(json.dumps({'evidence':{'source_file':'evidence.json','subject_id':subject,'subject_digest':digest}}).encode(),source=source)
        self.compare(b'{}')
    def test_original_invalid_json_error_messages_and_utf8_exceptions_are_preserved(self):
        for raw in (b'{',b'{"evidence":',b'\xff'):
            with self.subTest(raw=raw):self.compare(raw)
    def test_original_malformed_record_and_subject_structure_exceptions_are_not_coerced_to_success(self):
        for raw in (b'[]',b'null',b'{"evidence":null}',b'{"evidence":[]}',b'{"evidence":1}'):
            with self.subTest(raw=raw):self.compare(raw)
        for source in (b'[]',b'null',b'{"subjects":[1]}',b'{"subjects":null}'):
            with self.subTest(source=source):self.compare(b'{"evidence":{"source_file":"evidence.json","subject_id":"one"}}',source=source)
    def test_original_duplicate_json_keys_and_invalid_source_json_are_preserved(self):
        self.compare(b'{"evidence":null,"evidence":{}}')
        self.compare(b'{"evidence":{"source_file":"evidence.json","subject_id":"one"}}',source=b'{')
    def test_missing_record_directory_is_success_but_schema_is_still_required(self):
        files=ValidationFiles({'schemas/evidence-agent-provenance.schema.json':b'{}'})
        self.assertEqual(ProvenanceValidation(files).run()['returncode'],0)
        with self.assertRaises(FileNotFoundError):ProvenanceValidation(ValidationFiles({})).run()

if __name__=='__main__':unittest.main()
