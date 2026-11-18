"""Declared native release-observation replay; no native execution or authority."""
import base64
from copy import deepcopy
from pathlib import Path
import re
from types import SimpleNamespace

from lib.provider_ports import native_cleanup_observation_valid
from lib.portable.contracts import canonical_digest
from lib import release_reference_facts as facts
from lib.release_requests import ReleaseRequests,git_prefix

MAX_STREAM=65536
MAX_TOTAL=32*1024**2


class ReplayReleaseEnvironment(ReleaseRequests):
    def __init__(self,root,files,references,metadata,observations):
        super().__init__(root,files);facts.validate(references)
        if (not isinstance(metadata,dict) or set(metadata)!={'schema_version','capsule_root','tools'}
                or type(metadata['schema_version']) is not int or metadata['schema_version']!=1
                or not isinstance(metadata['capsule_root'],str) or not Path(metadata['capsule_root']).is_absolute()
                or str(Path(metadata['capsule_root']))!=metadata['capsule_root']
                or '..' in Path(metadata['capsule_root']).parts or len(metadata['capsule_root'])>8192
                or any(ord(c)<32 for c in metadata['capsule_root'])
                or not isinstance(metadata['tools'],dict) or set(metadata['tools'])!={'git','ssh-keygen'}
                or not isinstance(observations,list) or len(observations)>16384):
            raise ValueError('invalid_release_replay_context')
        for pair in metadata['tools'].values():
            if (not isinstance(pair,list) or len(pair)!=2 or not all(isinstance(v,str) for v in pair)
                    or not Path(pair[0]).is_absolute() or str(Path(pair[0]))!=pair[0] or '..' in Path(pair[0]).parts
                    or len(pair[0])>8192 or any(ord(c)<32 for c in pair[0])
                    or not re.fullmatch('[a-f0-9]{64}',pair[1])):
                raise ValueError('invalid_release_replay_tool_binding')
        self.metadata=deepcopy(metadata);self.tools=self.metadata['tools'];self.capsule=Path(metadata['capsule_root'])
        self.prefix=git_prefix(self.tools,self.capsule);self.observations=deepcopy(observations)
        self.position=0;self.total=0;self.staged_count=0
        self.consume({'stage':'capsule-init','object_format':references['object_format']},'git',
            self.prefix+['init','--bare','--template=','-b','release-capsule','--object-format='+references['object_format']],success=True)
        for oid,row in sorted(references['objects'].items()):
            result=self.consume({'stage':'capsule-object','oid':oid,'kind':row['kind']},'git',
                self.prefix+['hash-object','-w','--stdin','-t',row['kind']],success=True)
            if result.stdout.decode('ascii').strip()!=oid:raise ValueError('release_replay_object_write_changed')
        for name,oid in sorted(references['refs'].items()):
            self.consume({'stage':'capsule-ref','name':name,'oid':oid},'git',self.prefix+['update-ref','refs/tags/'+name,oid],success=True)

    def stage(self,raw):
        self.staged_count+=1
        if self.staged_count>4096:raise ValueError('release_native_staging_budget')
        return str(self.capsule/'inputs'/str(self.staged_count))

    def run(self,command,**kwargs):
        request=self.request(command,**kwargs);operation=request['operation']
        if command[0]=='git':
            arguments=command[1:]
            if operation=='verify-tag':
                allowed=self.stage(self.temporary_bytes(command[2].split('=',1)[1]))
                arguments=['-c','gpg.ssh.allowedSignersFile='+allowed,*command[3:]]
            argv=self.prefix+arguments
        else:
            argv=[self.tools['ssh-keygen'][0],*command[1:]]
            if operation=='signer-fingerprint':argv[2]=self.stage(self.temporary_bytes(command[2]))
            else:
                argv[4]=self.stage(self.temporary_bytes(command[4]));argv[10]=self.stage(self.source_bytes(command[10]))
        result=self.consume({'stage':'decision','request':request},command[0],argv)
        if not request['text']:return result
        return SimpleNamespace(returncode=result.returncode,
            stdout=result.stdout.decode('utf-8').replace('\r\n','\n').replace('\r','\n'),
            stderr=result.stderr.decode('utf-8').replace('\r\n','\n').replace('\r','\n'))

    def consume(self,request,tool,argv,*,success=False):
        if self.position>=len(self.observations):raise ValueError('release_native_observation_missing')
        row=self.observations[self.position]
        keys={'request','tool','tool_path','tool_sha256','ssh_tool_path','ssh_tool_sha256','argv','process_started',
            'returncode','timed_out','output_truncated','error_type','cleanup_signal_permission_denied','cleanup_absence_check','stdout_base64','stderr_base64'}
        if (not isinstance(row,dict) or set(row)!=keys or canonical_digest(row['request'])!=canonical_digest(request)
                or row['tool']!=tool or row['argv']!=argv or row['tool_path']!=self.tools[tool][0]
                or row['tool_sha256']!=self.tools[tool][1] or row['ssh_tool_path']!=self.tools['ssh-keygen'][0]
                or row['ssh_tool_sha256']!=self.tools['ssh-keygen'][1] or row['process_started'] is not True
                or type(row['returncode']) is not int or not -128<=row['returncode']<=255
                or success and row['returncode']!=0 or row['timed_out'] is not False
                or row['output_truncated'] is not False or row['error_type'] is not None
                or not native_cleanup_observation_valid(row)):
            raise ValueError('release_native_observation_changed_or_incomplete')
        streams={}
        for name in ('stdout','stderr'):
            value=row[name+'_base64']
            if not isinstance(value,str) or len(value)>4*((MAX_STREAM+2)//3):raise ValueError('release_native_observation_budget')
            try:raw=base64.b64decode(value,validate=True)
            except ValueError:raise ValueError('invalid_release_native_observation_bytes') from None
            if base64.b64encode(raw).decode('ascii')!=value:raise ValueError('invalid_release_native_observation_bytes')
            self.total+=len(raw)
            if len(raw)>MAX_STREAM or self.total>MAX_TOTAL:raise ValueError('release_native_observation_budget')
            streams[name]=raw
        self.position+=1
        return SimpleNamespace(returncode=row['returncode'],**streams)

    def finish(self):
        if self.position!=len(self.observations):raise ValueError('release_native_observation_unused')
