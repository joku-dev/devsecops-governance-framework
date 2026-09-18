"""Bounded ZIP extraction for externally supplied governance evidence."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import zipfile


DEFAULT_MAX_MEMBERS = 4096
DEFAULT_MAX_MEMBER_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_COMPRESSION_RATIO = 1000
COPY_CHUNK_BYTES = 1024 * 1024


def _validated_target(root: Path, info: zipfile.ZipInfo) -> Path:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    windows_path = PureWindowsPath(info.filename)
    if (
        not name
        or name.startswith("/")
        or path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in path.parts
        or any(ord(character) < 32 for character in name)
    ):
        raise ValueError(f"Unsafe ZIP member path: {info.filename!r}")

    mode = info.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    expected_types = {0, stat.S_IFDIR} if info.is_dir() else {0, stat.S_IFREG}
    if stat.S_ISLNK(mode) or file_type not in expected_types:
        raise ValueError(f"Unsupported ZIP member type: {info.filename!r}")
    if info.flag_bits & 1:
        raise ValueError(f"Encrypted ZIP member is unsupported: {info.filename!r}")

    target = root.joinpath(*path.parts)
    if not target.resolve(strict=False).is_relative_to(root):
        raise ValueError(f"ZIP member escapes extraction directory: {info.filename!r}")
    return target


def safe_extract_zip(
    archive_path: Path,
    destination: Path,
    *,
    max_members: int = DEFAULT_MAX_MEMBERS,
    max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_compression_ratio: int = DEFAULT_MAX_COMPRESSION_RATIO,
) -> None:
    """Extract a ZIP after validating every member and enforcing resource limits."""
    root = destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise ValueError(f"ZIP contains too many members: {len(members)} > {max_members}")

        validated: list[tuple[zipfile.ZipInfo, Path]] = []
        targets: set[str] = set()
        total = 0
        for info in members:
            target = _validated_target(root, info)
            target_key = str(target.relative_to(root)).casefold()
            if target_key in targets:
                raise ValueError(f"ZIP contains a duplicate target: {info.filename!r}")
            targets.add(target_key)
            if info.file_size < 0 or info.file_size > max_member_bytes:
                raise ValueError(f"ZIP member exceeds size limit: {info.filename!r}")
            total += info.file_size
            if total > max_total_bytes:
                raise ValueError("ZIP uncompressed size exceeds total limit")
            if info.file_size and (
                info.compress_size <= 0
                or info.file_size > info.compress_size * max_compression_ratio
            ):
                raise ValueError(f"ZIP member exceeds compression-ratio limit: {info.filename!r}")
            validated.append((info, target))

        for info, target in validated:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                raise ValueError(f"ZIP target already exists: {info.filename!r}")
            written = 0
            try:
                with archive.open(info) as source, target.open("xb") as output:
                    while chunk := source.read(COPY_CHUNK_BYTES):
                        written += len(chunk)
                        if written > info.file_size or written > max_member_bytes:
                            raise ValueError(f"ZIP member expanded beyond declared size: {info.filename!r}")
                        output.write(chunk)
            except Exception:
                target.unlink(missing_ok=True)
                raise
            if written != info.file_size:
                target.unlink(missing_ok=True)
                raise ValueError(f"ZIP member size differs from declaration: {info.filename!r}")
