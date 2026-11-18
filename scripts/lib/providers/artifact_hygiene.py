"""Explicit bounded local files/Office ZIP/environment acquisition; never execute files."""
import io
import os
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from lib.result_bytes import safe_bytes

MAX_FILE = 16 * 1024**2
MAX_TOTAL = 64 * 1024**2
MAX_MEMBERS = 2048
MAX_PATHS = 1024
MAX_LABEL = 4096
ENVIRONMENT = 'PUBLIC_ARTIFACT_FORBIDDEN_TERMS'


def environment_terms():
    return os.environ.get(ENVIRONMENT, '')


def capture(paths):
    if len(paths) > MAX_PATHS:
        raise ValueError('artifact_hygiene_path_budget')
    remaining = MAX_TOTAL
    texts = []
    label_bytes = 0

    def append(label, text):
        nonlocal remaining, label_bytes
        label_bytes += len(label.encode('utf-8'))
        if len(texts) >= 8192 or label_bytes > 1024**2:
            raise ValueError('artifact_hygiene_location_budget')
        remaining -= len(text.encode('utf-8'))
        if remaining < 0:
            raise ValueError('artifact_hygiene_text_budget')
        texts.append((label, text))

    def plain(raw):
        # Path.read_text uses universal newlines; ZIP member decode does not.
        return raw.decode('utf-8', errors='ignore').replace('\r\n', '\n').replace('\r', '\n')

    for path in map(Path, paths):
        label = str(path)
        if len(label) > MAX_LABEL or any(ord(c) < 32 for c in label):
            raise ValueError('artifact_hygiene_path_label')
        if path.is_symlink():
            raise ValueError('artifact_hygiene_symlink')
        if not path.exists() or path.is_dir():
            continue
        raw = safe_bytes(path, limit=min(MAX_FILE, remaining))
        remaining -= len(raw)
        if path.suffix.lower() not in ('.xlsx', '.docx', '.pptx'):
            append(label, plain(raw))
            continue
        try:
            with ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
                if len(names) > MAX_MEMBERS:
                    raise ValueError('artifact_hygiene_zip_member_budget')
                for name in names:
                    if len(name) > MAX_LABEL or any(ord(c) < 32 for c in name):
                        raise ValueError('artifact_hygiene_member_label')
                    # Original name lookup deliberately selects the last duplicate.
                    info = archive.getinfo(name)
                    if info.flag_bits & 1 or info.compress_type not in (0, 8, 12, 14):
                        raise ValueError('artifact_hygiene_unsupported_zip_member')
                    if info.file_size > min(MAX_FILE, remaining):
                        raise ValueError('artifact_hygiene_zip_byte_budget')
                    with archive.open(name) as member:
                        data = member.read(min(MAX_FILE, remaining) + 1)
                    if len(data) > min(MAX_FILE, remaining):
                        raise ValueError('artifact_hygiene_zip_byte_budget')
                    remaining -= len(data)
                    try:
                        text = data.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                    append(f'{label}:{name}', text)
        except BadZipFile:
            # Preserve already yielded members before the original fallback.
            append(label, plain(raw))
    return texts
