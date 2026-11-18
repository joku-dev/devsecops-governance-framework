"""Bounded read-only local Git capture for the complete release-reference scope."""
import base64
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat


from lib import review_git
from lib import release_reference_facts as facts
from lib.portable.contracts import canonical_digest
from lib.validation_files import MAX_FILES,MAX_TOTAL,relative
from lib.providers.validation_worktree import directory,file_bytes,signature
from lib.release_inputs import collect,POLICY


class ReleaseReferences:
    def __init__(self,root):
        self.root=Path(root).resolve()
        actual=review_git.git(self.root,'rev-parse','--show-toplevel').decode('utf-8').strip()
        if Path(actual).resolve()!=self.root:raise ValueError('release_repository_root_required')

    def refs(self):
        names=set()
        for pattern in ('*baseline*','v*-public-adoption'):
            raw=review_git.git(self.root,'-c','color.ui=false','-c','column.ui=never','tag','--list',pattern,limit=1024**2)
            for name in raw.decode('utf-8').splitlines():
                facts.release_name(name);names.add(name)
                if len(names)>facts.MAX_REFS:raise ValueError('release_reference_count_budget')
        return {name:review_git.git(self.root,'rev-parse','--verify','--end-of-options','refs/tags/'+name).decode('ascii').strip() for name in sorted(names)}

    def capture(self):
        algorithm=review_git.git(self.root,'rev-parse','--show-object-format').decode('ascii').strip()
        head=review_git.git(self.root,'rev-parse','--verify','HEAD^{commit}').decode('ascii').strip()
        tree=review_git.git(self.root,'rev-parse','--verify','HEAD^{tree}').decode('ascii').strip()
        facts.object_id(head,algorithm);facts.object_id(tree,algorithm)
        refs=self.refs();objects={};pending=list(refs.values());total=0
        while pending:
            oid=facts.object_id(pending.pop(),algorithm)
            if oid in objects:continue
            if len(objects)>=facts.MAX_OBJECTS:raise ValueError('release_reference_count_budget')
            kind=review_git.git(self.root,'cat-file','-t',oid,limit=32).decode('ascii').strip()
            if kind not in facts.KINDS:raise ValueError('invalid_release_object_type')
            raw=review_git.git(self.root,'cat-file',kind,oid,limit=facts.MAX_OBJECT)
            total+=len(raw)
            if total>facts.MAX_TOTAL:raise ValueError('release_object_total_budget')
            if facts.digest(kind,raw,algorithm)!=oid:raise ValueError('release_native_object_changed')
            objects[oid]={'kind':kind,'base64':base64.b64encode(raw).decode('ascii'),'sha256':hashlib.sha256(raw).hexdigest()}
            if kind=='tag':pending.append(facts.tag_target(raw,algorithm)[0])
        value={'schema_version':1,'source_head':head,'source_tree':tree,'object_format':algorithm,'refs':refs,'objects':objects}
        facts.validate(value)
        if (self.refs()!=refs or review_git.git(self.root,'rev-parse','--verify','HEAD^{commit}').decode('ascii').strip()!=head):
            raise ValueError('release_references_changed_during_capture')
        return value


class ReleaseSource:
    """Held ordinary input files and explicit actual Git refs at the product base."""
    POLICY=POLICY
    def __init__(self,source,revision):
        source=Path(source)
        if source.is_symlink():raise ValueError('ordinary_release_source_required')
        self.source=source.resolve(strict=True);self.revision=revision
        self.references=ReleaseReferences(self.source)

    def capture(self):
        references=self.references.capture()
        if references['source_head']!=self.revision:raise ValueError('release_source_product_revision_mismatch')
        fd=os.open(self.source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        before=os.fstat(fd);data={};absent=set();requested=set();total=0
        def read(name):
            nonlocal total
            if not isinstance(name,str):return None
            relative(name)
            if any(part.casefold()=='.git' for part in Path(name).parts):raise ValueError('release_git_metadata_artifact_forbidden')
            if name in requested:return data.get(name)
            requested.add(name)
            if len(requested)>MAX_FILES:raise ValueError('release_input_count_budget')
            parts=Path(name).parts
            if not parts:absent.add(name);return None
            if len(parts)>100:raise ValueError('release_input_depth_budget')
            with ExitStack() as stack:
                parent=fd
                for part in parts[:-1]:
                    parent=stack.enter_context(directory(parent,part))
                    if parent is None:absent.add(name);return None
                try:meta=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError:absent.add(name);return None
                if stat.S_ISDIR(meta.st_mode):absent.add(name);return None
                if not stat.S_ISREG(meta.st_mode):raise ValueError('unsafe_release_input_file')
                raw=file_bytes(parent,parts[-1]);total+=len(raw)
                if total>MAX_TOTAL:raise ValueError('release_input_total_budget')
                data[name]=raw;return raw
        try:
            collect(read)
            if (signature(before)!=signature(os.fstat(fd))
                    or signature(before)!=signature(os.stat(self.source,follow_symlinks=False))
                    or canonical_digest(self.references.capture())!=canonical_digest(references)):
                raise ValueError('release_source_changed_during_capture')
            manifest={'schema_version':1,'scope':'explicit-release-verification-data-v1','source_root':str(self.source),
                'commit':self.revision,'tree':references['source_tree'],'references_digest':canonical_digest(references),
                'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in sorted(data.items())},
                'absent':sorted(absent)}
            return data,manifest,references
        finally:os.close(fd)
