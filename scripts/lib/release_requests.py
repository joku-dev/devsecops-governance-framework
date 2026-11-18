"""Finite release-verifier requests and deterministic inert temporary text files."""
import base64
import io
from pathlib import Path, PurePosixPath
import shlex

from lib.release_reference_facts import release_name
from lib.validation_files import ValidationFiles

MAX_TEMPORARY=65536


def git_prefix(tools,capsule):
    return [tools['git'][0],'--no-optional-locks','--literal-pathspecs',
        '-c','safe.directory='+str(capsule),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',
        '-c','protocol.allow=never','-c','gpg.format=ssh','-c','gpg.ssh.program='+shlex.quote(tools['ssh-keygen'][0])]


class TemporaryText(io.StringIO):
    def __init__(self,owner,name):super().__init__();self.owner=owner;self.name=name
    def write(self,value):
        if not isinstance(value,str) or len(value.encode('utf-8'))>MAX_TEMPORARY:raise ValueError('release_temporary_file_budget')
        result=super().write(value)
        if len(self.getvalue().encode('utf-8'))>MAX_TEMPORARY:raise ValueError('release_temporary_file_budget')
        return result
    def flush(self):
        if not self.closed:self.owner.temporary[self.name]=self.getvalue().encode('utf-8')
    def close(self):
        if not self.closed:self.flush()
        super().close()


class ReleaseRequests:
    def __init__(self,root,files,*,label_only=False):
        if type(label_only) is not bool:raise ValueError('release_path_profile_required')
        self.label_only=label_only
        self.root=self.path(root);ValidationFiles(files);self.files=dict(files)
        self.temporary={};self.temporary_count=0

    def path(self,value):
        if not self.label_only:return Path(value).resolve()
        text=str(value);path=PurePosixPath(text)
        if (not path.is_absolute() or str(path)!=text or '..' in path.parts
                or len(text)>8192 or any(ord(c)<32 for c in text)):
            raise ValueError('canonical_release_replay_label_required')
        return path

    def temporary_file(self,mode,*,encoding):
        if mode!='w' or encoding!='utf-8':raise ValueError('unsupported_release_temporary_file')
        self.temporary_count+=1
        if self.temporary_count>1024:raise ValueError('release_temporary_file_count_budget')
        name=str(self.root.parent/'native-release-temporary'/str(self.temporary_count))
        self.temporary[name]=b''
        return TemporaryText(self,name)

    def temporary_bytes(self,name):
        if name not in self.temporary:raise ValueError('release_temporary_file_not_retained')
        return self.temporary[name]

    def source_bytes(self,name):
        path=Path(name)
        if not path.is_absolute() or not path.is_relative_to(self.root):raise ValueError('release_native_file_outside_input')
        relative=path.relative_to(self.root).as_posix()
        if relative not in self.files:raise ValueError('release_native_file_not_retained')
        return self.files[relative]

    def request(self,command,*,cwd=None,input=None,capture_output=False,text=False,check=False):
        if (not isinstance(command,list) or len(command)>16 or not all(isinstance(v,str) and len(v.encode())<=8192 and '\0' not in v for v in command)
                or capture_output is not True or check is not False or type(text) is not bool
                or input is not None and (not isinstance(input,bytes) or len(input)>1024**2)):
            raise ValueError('invalid_release_native_request')
        actual_cwd=None if cwd is None else str(self.path(cwd))
        if actual_cwd not in (None,str(self.root)):raise ValueError('release_native_cwd_not_retained')
        operation=None
        if len(command)==4 and command[:3]==['git','tag','--list'] and command[3] in ('*baseline*','v*-public-adoption'):
            operation='list-tags'
        elif len(command)==4 and command[:3]==['git','rev-parse','--verify']:
            value=command[3];name=value.removeprefix('refs/tags/').removesuffix('^{commit}')
            release_name(name)
            if value not in ('refs/tags/'+name,'refs/tags/'+name+'^{commit}'):raise ValueError('invalid_release_ref_operand')
            operation='tag-identity'
        elif len(command)==6 and command[:2]==['git','-c'] and command[3:5]==['verify-tag','--raw']:
            prefix='gpg.ssh.allowedSignersFile='
            if not command[2].startswith(prefix):raise ValueError('invalid_release_signer_option')
            self.temporary_bytes(command[2][len(prefix):]);release_name(command[5]);operation='verify-tag'
        elif len(command)==3 and command[:2]==['ssh-keygen','-lf']:
            self.temporary_bytes(command[2]);operation='signer-fingerprint'
        elif (len(command)==11 and command[:4]==['ssh-keygen','-Y','verify','-f']
                and command[5]=='-I' and command[7]=='-n' and command[9]=='-s'):
            self.temporary_bytes(command[4]);self.source_bytes(command[10]);operation='verify-manifest'
        if operation is None:raise ValueError('unsupported_release_native_command')
        if ((operation=='signer-fingerprint')!=(actual_cwd is None) or text!=(operation=='signer-fingerprint')
                or (operation!='verify-manifest' and input is not None)):
            raise ValueError('unsupported_release_native_context')
        return {'schema_version':1,'operation':operation,'command':command,'cwd':actual_cwd,
            'stdin_base64':None if input is None else base64.b64encode(input).decode('ascii'),'text':text}
