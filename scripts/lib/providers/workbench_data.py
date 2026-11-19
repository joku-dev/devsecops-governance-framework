"""Explicit local product and private-upload inputs for the complete Workbench."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import stat
from lib.result_bytes import strict_json
from lib.workbench_archive import checked_draft

from lib.review_git import git as git_read
from lib.report_data import ReportData
from lib.report_requirement_delta import extract_requirements
from lib.report_source_process import build_report
from lib.result_bytes import safe_bytes
from lib.source_document_text import extract_source_document_bytes


class WorkspaceData(ReportData):
    def __init__(self, root, membership, workspace, upload_label):
        super().__init__(root, membership)
        self.workspace = Path(workspace).resolve()
        self.upload_label = upload_label

    def relative(self, path):
        path = Path(path)
        if path.is_relative_to(self.workspace):
            relative = path.relative_to(self.workspace)
            # Only an explicitly created, private candidate source is readable.
            import re
            if (len(relative.parts) != 2 or not re.fullmatch('[a-f0-9]{32}', relative.parts[0])
                    or relative.parts[1] not in ('source.md', 'source.markdown', 'source.pdf', 'source.docx')
                    or path.is_symlink() or path.parent.is_symlink()):
                raise ValueError('invalid_workbench_upload_path')
            return self.upload_label + '/' + relative.as_posix()
        return super().relative(path)

    def is_file(self, path):
        self.relative(path)
        return Path(path).is_file()

    def is_dir(self, path):
        self.relative(path)
        return Path(path).is_dir()

    def exists(self, path):
        self.relative(path)
        return Path(path).exists()

    def iterdir(self, path):
        self.relative(path); rows = []
        for child in Path(path).iterdir():
            rows.append(child)
            if len(rows) > 10000: raise ValueError('workbench_input_membership_budget')
        return sorted(rows)

    def raw(self, path):
        path = Path(path)
        name = self.relative(path)
        if path.is_relative_to(self.workspace):
            return private_bytes(path, 5 * 1024**2)
        # V1's Workbench observes working model/source/report files, including
        # newly registered and unregistered source files. Never execute them.
        if name not in self.files and not any(name.startswith(prefix + '/') for prefix in
                ('model', 'schemas', 'status', 'generated/reports', 'docs/governance/source-documents')):
            raise ValueError('workbench_input_outside_data_scope')
        from lib.repository_capture import private_name
        if private_name(name): raise ValueError('private_workbench_source_forbidden')
        return safe_bytes(path, limit=16 * 1024**2)

    def extract(self, path):
        return extract_source_document_bytes(self.relative(path), self.raw(path))


class WorkbenchData:
    """No producer program runs; source and upload namespaces stay disjoint."""
    def __init__(self, root, workspace, *, live_process=True, instance=None):
        self.root = Path(root).resolve()
        self.workspace = Path(workspace).resolve()
        self.instance = Path(instance).resolve() if instance is not None else None
        self.live_process = live_process
        if self.instance is None:
            label = self.workspace.relative_to(self.root).as_posix()
            self.publications = self.workspace
        else:
            if self.workspace != self.instance/'state/workbench':
                raise ValueError('instance_owned_workbench_required')
            label = 'state/workbench'
            self.publications = self.instance/'state/workbench-publications'
        membership = {}
        for row in filter(None, git_read(self.root, 'ls-tree', '-r', '-z', 'HEAD').split(b'\0')):
            metadata, name = row.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            if kind != 'blob': raise ValueError('workbench_regular_source_required')
            membership[name.decode()] = {'mode': mode}
        self.data = WorkspaceData(self.root, membership, self.workspace, label)

    def bind(self, root, state):
        if Path(root).resolve() != self.root or Path(state).resolve() != self.workspace:
            raise ValueError('workbench_backend_binding_mismatch')

    def validate_folder(self, folder):
        if self.instance is None: return
        folder = Path(folder)
        import re
        if (folder.parent != self.workspace or not re.fullmatch('[a-f0-9]{32}', folder.name)
                or folder.is_symlink() or not folder.is_dir() or folder.stat().st_mode & 0o077
                or folder.stat().st_uid != os.geteuid()):
            raise ValueError('private_workbench_draft_directory_required')

    def draft(self, path):
        if self.instance is None:
            return json.loads(path.read_text())
        self.validate_folder(path.parent)
        value = strict_json(private_bytes(path, 16 * 1024**2).decode('utf-8'))
        schema = json.loads((self.root/'schemas/governance-workbench-draft.schema.json').read_bytes())
        try: return checked_draft(value, path.parent.name, schema)
        except ValueError as error:
            if str(error) == 'invalid_workbench_backup_draft':
                raise ValueError('invalid_private_workbench_draft') from None
            raise

    def validate_saved(self, folder, value):
        if self.instance is None: return
        schema = json.loads((self.root/'schemas/governance-workbench-draft.schema.json').read_bytes())
        checked_draft(value, Path(folder).name, schema)

    def head(self):
        return git_read(self.root, 'rev-parse', 'HEAD').decode().strip()

    def extract(self, path):
        return self.data.extract(path)

    def requirements(self, source_id, path, origin='unverified'):
        return extract_requirements(self.data, source_id, path, origin)

    def process_report(self):
        if not self.live_process:
            path = self.root/'generated/reports/source-document-process-status.json'
            return json.loads(path.read_text()) if path.is_file() else {}
        return build_report(self.data, datetime.now(timezone.utc).isoformat())

    def publication_destination(self, draft_id):
        if self.instance is not None:
            from lib.candidate_workspace import private_directory
            private_directory(self.publications)
        return self.publications/('pr-' + draft_id)


def private_bytes(path, limit):
    row = path.lstat()
    if (not stat.S_ISREG(row.st_mode) or row.st_uid != os.geteuid()
            or row.st_nlink != 1 or row.st_mode & 0o077):
        raise ValueError('private_workbench_file_required')
    raw = safe_bytes(path, limit=limit); after = path.lstat()
    if any(getattr(row, k) != getattr(after, k) for k in ('st_ino','st_dev','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')):
        raise ValueError('workbench_file_changed_during_read')
    return raw
