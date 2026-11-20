"""Explicit workbook/YAML admission; never an original business verdict."""
import io
from zipfile import ZipFile
from lib.requirement_validation_budget import InputAdmissionError,yaml_text
MAX_COMPRESSED=16*1024**2
MAX_MEMBER=16*1024**2
MAX_EXPANDED=32*1024**2
MAX_MEMBERS=4096


def workbook_archive(path):
    raw=path.read_bytes()
    if len(raw)>MAX_COMPRESSED:raise InputAdmissionError('workbook_import_compressed_budget')
    archive=ZipFile(io.BytesIO(raw))
    try:
        members=archive.infolist()
        if len(members)>MAX_MEMBERS or any(m.file_size>MAX_MEMBER for m in members) or sum(m.file_size for m in members)>MAX_EXPANDED:
            raise InputAdmissionError('workbook_import_archive_budget')
        return archive
    except BaseException:
        archive.close();raise
