"""Complete own-product suite composition over one exact private source overlay.

All executed programs are admitted own code. The source/package/node are explicit;
no inspected consumer or working-tree program can select a command or execute.
"""
import base64
import hashlib
import json

from lib.provenance_validation import ProvenanceValidation
from lib.validation_application import ValidationContext,retained_files
from lib.validation_files import ValidationFiles
from lib.result_bytes import safe_bytes
from lib.providers.compliance_native import NativeComplianceEnvironment


class FullSuite:
    def __init__(self,session):
        from lib.v2_application import instance,initialize
        options=session.options
        node=options['instance']
        if not node.exists():initialize(node,opa=session.target/'bin/opa')
        actual,settings=instance(node)
        if settings['development']:raise ValueError('validation_suite_committed_instance_required')
        self.session=session
        self.backend=NativeComplianceEnvironment(instance_root=actual,package=options['package'],
            package_pin=options['sha256'],workarea=session.journal.root/'work',at=options['at'],
            output_file=session.journal.root/'unused-export.json',cwd=session.journal.root,
            on_event=lambda row:session.journal.append({'kind':'own-suite-component','observation':row}),
            perform_preflight=False,require_source_intake=False)
        self.session.journal.append({'kind':'own-suite-source','source_revision':self.backend.revision,
            'source_tree':self.backend.manifest['source_tree'],'package_sha256':options['sha256'],
            'initial_files':self.backend.before,'references':self.backend.references})

    def runtime_validation(self):
        backend=self.backend;backend.checkpoint()
        context=ValidationContext(backend.instance,backend.settings)
        identifier,value=context.create(backend.at,source_worktree=backend.root)
        checked=context.inspect(identifier)
        self.session.journal.retain_component('runtime',identifier,context.operations/identifier)
        if value['execution']!='complete' or checked!=value:
            raise ValueError('validation_suite_runtime_execution_incomplete')
        target=context.operations/identifier
        inputs=retained_files(target/'inputs',json.loads((target/'input-manifest.json').read_bytes())['files'])
        outputs=retained_files(target/'outputs',value['output_files'])
        if not inputs.keys()<=outputs.keys():raise ValueError('validation_suite_runtime_membership_changed')
        for name,raw in outputs.items():
            old=safe_bytes(backend.root/name) if name in backend.expected else None
            if name in inputs and old!=inputs[name]:raise ValueError('validation_suite_runtime_input_changed')
            if raw==old:continue
            if not name.startswith('generated/'):raise ValueError('validation_suite_runtime_nondiagnostic_write')
            self.session.journal.append({'kind':'own-suite-runtime-write','path':name,'assessment':identifier,
                'before_sha256':None if old is None else hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(raw).hexdigest()})
            path=backend.root/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_bytes(raw)
            backend.expected[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'mode':backend.expected.get(name,{}).get('mode','100644')}
            backend.generated_baseline[name]=raw
        backend.checkpoint()
        self.session.journal.append({'kind':'own-suite-runtime','assessment':identifier,'outcome':{
            k:value[k] for k in ('execution','exit_code','input_id','source_tree','output_files')}})
        return {'returncode':value['exit_code'],'stdout':base64.b64decode(value['stdout_base64']),
                'stderr':base64.b64decode(value['stderr_base64'])}

    def repository_validation(self):
        result=self.backend.repository()
        identifier=self.backend.suboperations[-1]['assessment_id']
        component=self.backend.instance/'state/repository-validation/operations'/identifier
        self.session.journal.retain_component('repository',identifier,component)
        if self.backend.suboperations[-1]['execution']!='complete':
            raise ValueError('validation_suite_repository_execution_incomplete')
        return {'returncode':result.returncode,'stdout':result.stdout.encode(),'stderr':result.stderr.encode()}

    def provenance_validation(self):
        backend=self.backend;backend.checkpoint()
        names={n for n in backend.expected if n.startswith('status/evidence-agent-provenance/') or n=='schemas/evidence-agent-provenance.schema.json'}
        files={n:safe_bytes(backend.root/n) for n in names}
        # Resolve only admitted same-source members, never live ambient files.
        for name,raw in list(files.items()):
            if not name.startswith('status/'):continue
            try:source=json.loads(raw).get('evidence',{}).get('source_file')
            except (ValueError,AttributeError,TypeError):continue
            if type(source) is str and source in backend.expected:files[source]=safe_bytes(backend.root/source)
        from lib.providers.validation_suite_storage import raw_new
        from lib.providers.environment_bootstrap_storage import write_new
        retained=self.session.journal.root/'provenance-inputs';retained.mkdir(mode=0o700)
        descriptors={}
        for number,(name,raw) in enumerate(sorted(files.items())):
            descriptors[name]=raw_new(retained/f'{number:05d}.bin',raw)
        pin=write_new(retained/'manifest.json',{'files':descriptors,'membership':sorted(backend.expected),'label':str(backend.root)})
        self.session.journal.append({'kind':'own-suite-provenance-inputs','manifest':pin})
        result=ProvenanceValidation(ValidationFiles(files,backend.expected,label=str(backend.root))).run()
        backend.checkpoint();return {'returncode':result['returncode'],'stdout':result['stdout'].encode(),'stderr':result['stderr'].encode()}

    def unit_tests(self):
        result=self.backend.unit_tests()
        self.session.journal.append({'kind':'own-suite-unit-outcome','native_outcome':self.backend.unit_outcome,
            'statistics':self.backend.unit_statistics,'final_files':self.backend.expected,
            'viewer_projection':self.backend.projection,'native_root':str(self.backend.native)})
        return {'returncode':result.returncode,'stdout':result.stdout.encode(),'stderr':result.stderr.encode()}
