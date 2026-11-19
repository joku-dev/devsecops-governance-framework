"""Original standalone provenance validation decisions over an explicit data view.

This compatibility engine preserves original JSON/error ordering and malformed
shape exceptions. Data-view adapters bound reads; they grant no subject, agency,
source or operating authority, and no caller program executes here.
"""
import json
from jsonschema import Draft202012Validator
from lib.evidence_agent_provenance import load_subject_digest


class ProvenanceValidation:
    def __init__(self,files):self.root=files.root
    def validate_record(self,path,schema):
        errors=[]
        try:record=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as error:return [f'{path}: cannot read JSON: {error}']
        errors.extend(f'{path}: {error.message}' for error in Draft202012Validator(schema).iter_errors(record))
        source_file=record.get('evidence',{}).get('source_file')
        if not source_file:return errors
        source_path=self.root/source_file
        if not source_path.is_file():
            errors.append(f'{path}: evidence source file does not exist: {source_file}');return errors
        try:source_payload=json.loads(source_path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as error:
            errors.append(f'{path}: evidence source file is not valid JSON: {error}');return errors
        subject=record.get('evidence',{})
        actual=load_subject_digest(source_payload,subject.get('subject_id',''))
        if actual is None:errors.append(f"{path}: subject is not present in source file: {subject.get('subject_id','unknown')}")
        elif actual!=subject.get('subject_digest'):errors.append(f'{path}: subject digest does not match source file')
        return errors
    def run(self):
        schema=json.loads((self.root/'schemas/evidence-agent-provenance.schema.json').read_text(encoding='utf-8'))
        errors=[];records=self.root/'status/evidence-agent-provenance'
        if records.exists():
            for path in sorted(records.rglob('*.json')):errors.extend(self.validate_record(path,schema))
        return {'returncode':1 if errors else 0,'stdout':'' if errors else 'Evidence agent provenance validation passed\n',
                'stderr':('Evidence agent provenance validation failed\n'+'\n'.join(errors)+'\n') if errors else ''}
