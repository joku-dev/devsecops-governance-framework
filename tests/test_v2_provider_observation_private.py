"""Entire original file/ACL/mount checks on real files and explicit systemd facets."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import ast,copy,os,re,stat,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.provider_observation_private import PrivateCredentialCheck
from lib.v2_boundary import violations
FIXTURE=ROOT/'tests/fixtures/v2-provider-observation-original/private-credentials.txt'


def original(path_factory=Path,native=os,system=sys):
    scope={'os':native,'Path':path_factory,'sys':system,'stat':stat,'struct':struct,'re':re};nodes=[copy.deepcopy(n) for n in ast.parse(FIXTURE.read_bytes()).body if isinstance(n,ast.FunctionDef)];exec(compile(ast.Module(body=nodes,type_ignores=[]),'immutable_original_private_credentials','exec'),scope);return scope


def outcome(function,*args):
    try:return {'returned':function(*args)}
    except Exception as error:return {'type':type(error).__name__,'message':str(error)}


class WholePrivateCredentialDecisions(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name).resolve();self.file=self.base/'credential';self.file.write_bytes(b'Only synthetic credential fixture\n');self.model=PrivateCredentialCheck(path_factory=Path,native=os,system=sys);self.old=original()
    def compare(self,path):
        expected=outcome(self.old['check_private_file'],path);actual=outcome(self.model.check_private_file,path);self.assertEqual(actual,expected);return actual
    def test_original_owned_private_files_and_unsafe_permissions(self):
        for mode in (0o600,0o400,0o644,0o640):
            with self.subTest(mode=oct(mode)):
                self.file.chmod(mode);value=self.compare(self.file)
                if mode&0o077:self.assertEqual(value['type'],'ValueError')
                else:self.assertEqual(value,{'returned':None})
    def test_original_missing_symlink_directory_and_hardlink_failures(self):
        self.assertEqual(self.compare(self.base/'missing')['type'],'FileNotFoundError');link=self.base/'alias';link.symlink_to(self.file);self.assertEqual(self.compare(link)['message'],'Private file must not be a symlink');self.assertEqual(self.compare(self.base)['type'],'ValueError');alias=self.base/'hardlink';os.link(self.file,alias);self.assertEqual(self.compare(self.file)['message'],'Expected an owned private regular file')
    def test_native_descriptor_is_closed_in_the_original_finally_on_failure(self):
        trace=[]
        class Native:
            O_RDONLY=os.O_RDONLY;O_NOFOLLOW=os.O_NOFOLLOW;environ=os.environ
            def open(this,*args):fd=os.open(*args);trace.append(('open',fd));return fd
            def fstat(this,fd):trace.append(('fstat',fd));return os.fstat(fd)
            def geteuid(this):return os.geteuid()
            def close(this,fd):trace.append(('close',fd));os.close(fd)
        self.file.chmod(0o644)
        for selected in ('original','model'):
            trace.clear();native=Native();function=original(native=native)['check_private_file'] if selected=='original' else PrivateCredentialCheck(path_factory=Path,native=native,system=sys).check_private_file
            self.assertEqual(outcome(function,self.file)['type'],'ValueError');self.assertEqual([x[0] for x in trace],['open','fstat','close'])
            with self.assertRaises(OSError):os.fstat(trace[0][1])
    def systemd(self,*,mount='ro',acl_uid=123,platform='linux',parent_mode=0o550):
        directory='/run/credentials/fixture.service';reads=[]
        class FacetPath(PurePosixPath):
            def is_symlink(this):return False
            def resolve(this):return this
            def stat(this):return SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR|parent_mode)
            def read_text(this):
                reads.append(str(this));return '35 29 0:32 / '+directory+' '+mount+' - tmpfs tmpfs ro\n'
        def acl(permission):
            entries=[(1,permission,0xffffffff),(2,permission,acl_uid),(4,0,0xffffffff),(16,permission,0xffffffff),(32,0,0xffffffff)]
            return struct.pack('<I',2)+b''.join(struct.pack('<HHI',*row) for row in entries)
        native=SimpleNamespace(O_RDONLY=0,O_NOFOLLOW=131072,environ={'CREDENTIALS_DIRECTORY':directory},open=lambda *a:7,close=lambda fd:None,geteuid=lambda:123,fstat=lambda fd:SimpleNamespace(st_mode=stat.S_IFREG|0o440,st_nlink=1,st_uid=0),getxattr=lambda path,key:acl(4 if type(path) is int else 5))
        path=FacetPath(directory+'/credential');system=SimpleNamespace(platform=platform);expected=outcome(original(FacetPath,native,system)['check_private_file'],path);reads.clear();actual=outcome(PrivateCredentialCheck(path_factory=FacetPath,native=native,system=system).check_private_file,path);self.assertEqual(actual,expected);return actual,reads
    def test_whole_systemd_readonly_mount_exact_ACLs_and_unknown_facets(self):
        self.assertEqual(self.systemd()[0],{'returned':None})
        for options in ({'mount':'rw'},{'acl_uid':456},{'platform':'darwin'},{'parent_mode':0o750}):
            with self.subTest(options=options):
                value,reads=self.systemd(**options);self.assertEqual(value['type'],'ValueError')
                if options.get('platform')=='darwin':self.assertEqual(reads,[])
    def test_complete_original_three_function_AST_and_neutral_boundary(self):
        old={n.name:n for n in ast.parse(FIXTURE.read_bytes()).body if isinstance(n,ast.FunctionDef)};path=ROOT/'scripts/lib/provider_observation_private.py';tree=ast.parse(path.read_bytes());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef));actual={n.name:n for n in klass.body if isinstance(n,ast.FunctionDef)};self.assertEqual(set(actual)-{'__init__'},set(old));aliases={'native':'os','path':'Path','system':'sys','_service_acl':'_service_acl','_readonly_memory_mount':'_readonly_memory_mount'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=='self' and node.attr in aliases:return ast.copy_location(ast.Name(aliases[node.attr],node.ctx),node)
                return self.generic_visit(node)
        for name,node in old.items():
            value=copy.deepcopy(actual[name]);value.args.args.pop(0);value=Restore().visit(value);self.assertEqual(ast.dump(value,include_attributes=False),ast.dump(node,include_attributes=False))
        self.assertEqual(violations('scripts/lib/provider_observation_private.py',path.read_text()),[])
    def test_entire_binary_ACL_helper_rejects_extra_missing_and_wrong_entries(self):
        valid=struct.pack('<I',2)+b''.join(struct.pack('<HHI',*row) for row in [(1,4,0xffffffff),(2,4,123),(4,0,0xffffffff),(16,4,0xffffffff),(32,0,0xffffffff)])
        for raw in (valid,valid[:-1],valid+b'\0'*8,valid[:4]+b'\0'*40):
            with self.subTest(raw_length=len(raw)):self.assertEqual(self.model._service_acl(raw,123,4),self.old['_service_acl'](raw,123,4))
