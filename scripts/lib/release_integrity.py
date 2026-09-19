"""Cryptographic verification for governance release tags."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "model/governance/release-signing-policy.yaml"


def _run(root: Path, command: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=root,
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    candidate = root / relative
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"Release integrity path escapes the repository: {relative}")
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"Release integrity file is missing or is a symlink: {relative}")
    return candidate


def _validate_checksum_file(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            errors.append(f"Invalid checksum entry {path}:{number}")
            continue
        expected, relative = parts[0].lower(), parts[1].lstrip("* ")
        try:
            target = _safe_file(root, relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        actual = _sha256(target)
        if actual != expected:
            errors.append(f"Checksum mismatch for {relative}: expected {expected}, got {actual}")
    return errors


def _tag_names(root: Path) -> list[str]:
    names: set[str] = set()
    for pattern in ("*baseline*", "v*-public-adoption"):
        result = _run(root, ["git", "tag", "--list", pattern])
        if result.returncode != 0:
            raise ValueError(result.stderr.decode().strip() or "Unable to list release tags")
        names.update(item for item in result.stdout.decode().splitlines() if item)
    return sorted(names)


def _tag_identity(root: Path, tag: str) -> tuple[str, str]:
    tag_object = _run(root, ["git", "rev-parse", "--verify", f"refs/tags/{tag}"])
    target = _run(root, ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"])
    if tag_object.returncode != 0 or target.returncode != 0:
        raise ValueError(f"Unable to resolve release tag {tag}")
    return tag_object.stdout.decode().strip(), target.stdout.decode().strip()


def _allowed_signers(policy: dict) -> str:
    lines = []
    for signer in policy["direct_signature"]["trusted_signers"]:
        if signer.get("status") == "active":
            with tempfile.NamedTemporaryFile("w", encoding="utf-8") as public_key:
                public_key.write(signer["public_key"] + "\n")
                public_key.flush()
                fingerprint = subprocess.run(
                    ["ssh-keygen", "-lf", public_key.name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            actual = fingerprint.stdout.split()[1] if fingerprint.returncode == 0 else None
            if actual != signer.get("fingerprint"):
                raise ValueError(
                    f"Release signer fingerprint mismatch for {signer['principal']}: "
                    f"expected {signer.get('fingerprint')}, got {actual}"
                )
            lines.append(f"{signer['principal']} {signer['public_key']}")
    if not lines:
        raise ValueError("Release signing policy has no active trusted signer")
    return "\n".join(lines) + "\n"


def _verify_manifest(root: Path, policy: dict, allowed_signers: Path) -> tuple[dict | None, list[str]]:
    config = policy["legacy_attestation"]
    errors: list[str] = []
    try:
        manifest_path = _safe_file(root, config["manifest"])
        signature_path = _safe_file(root, config["signature"])
    except ValueError as error:
        return None, [str(error)]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"Release integrity manifest is invalid: {error}"]
    if manifest.get("repository_id") != policy.get("repository_id"):
        errors.append("Release integrity manifest repository differs from policy")
    principals = {
        item["principal"] for item in policy["direct_signature"]["trusted_signers"]
        if item.get("status") == "active"
    }
    principal = manifest.get("signer_principal")
    if principal not in principals:
        errors.append("Release integrity manifest signer is not trusted")
    else:
        result = _run(
            root,
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(allowed_signers),
                "-I", principal,
                "-n", config["namespace"],
                "-s", str(signature_path),
            ],
            input_bytes=manifest_path.read_bytes(),
        )
        if result.returncode != 0:
            detail = result.stderr.decode().strip() or result.stdout.decode().strip()
            errors.append(f"Release integrity manifest signature is invalid: {detail}")
    return manifest, errors


def _manifest_records(root: Path, policy: dict, manifest: dict | None) -> tuple[dict[str, dict], list[str]]:
    errors: list[str] = []
    records: dict[str, dict] = {}
    for record in (manifest or {}).get("legacy_tags", []):
        name = record.get("tag_name")
        if not name or name in records:
            errors.append(f"Duplicate or missing legacy tag record: {name}")
            continue
        record_errors = []
        for artifact in record.get("artifacts", []):
            try:
                path = _safe_file(root, artifact["path"])
            except (KeyError, ValueError) as error:
                record_errors.append(str(error))
                continue
            actual = _sha256(path)
            if actual != artifact.get("sha256"):
                record_errors.append(
                    f"Artifact digest mismatch for {artifact.get('path')}: "
                    f"expected {artifact.get('sha256')}, got {actual}"
                )
            if artifact.get("role") == "package_checksums":
                record_errors.extend(_validate_checksum_file(root, path))
        if record_errors:
            errors.extend(f"{name}: {item}" for item in record_errors)
        records[name] = {**record, "validation_errors": record_errors}
    permitted = set(policy["legacy_attestation"]["permitted_unsigned_tags"])
    actual = set(records)
    if actual != permitted:
        errors.append(
            "Legacy manifest tag set differs from policy: "
            f"missing={sorted(permitted - actual)}, unexpected={sorted(actual - permitted)}"
        )
    return records, errors


def verify_release_integrity(root: Path = ROOT, policy_path: Path | None = None) -> dict:
    """Verify direct tag signatures and the bounded historical integrity manifest."""
    root = root.resolve()
    policy_file = policy_path or (root / DEFAULT_POLICY.relative_to(ROOT))
    policy = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
    tags = _tag_names(root)
    observations = []
    verification_errors: list[str] = []

    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as allowed:
        allowed.write(_allowed_signers(policy))
        allowed.flush()
        allowed_path = Path(allowed.name)
        manifest, manifest_errors = _verify_manifest(root, policy, allowed_path)
        records, record_errors = _manifest_records(root, policy, manifest)
        verification_errors.extend(manifest_errors)
        verification_errors.extend(record_errors)

        permitted = set(policy["legacy_attestation"]["permitted_unsigned_tags"])
        for tag in tags:
            tag_object, target_commit = _tag_identity(root, tag)
            direct = _run(
                root,
                [
                    "git", "-c", f"gpg.ssh.allowedSignersFile={allowed_path}",
                    "verify-tag", "--raw", tag,
                ],
            )
            if direct.returncode == 0:
                status = "verified"
                mode = "direct_signature_verified"
                detail = "Tag signature verified against an active release signer."
            elif tag in permitted:
                record = records.get(tag, {})
                identity_matches = (
                    record.get("tag_object_sha") == tag_object
                    and record.get("target_commit_sha") == target_commit
                )
                valid = not manifest_errors and not record.get("validation_errors") and identity_matches
                status = "verified" if valid else "unverified"
                mode = "legacy_manifest_verified" if valid else "none"
                detail = (
                    "Immutable historical tag and release artifacts match the signed retrospective manifest."
                    if valid
                    else "Historical tag does not match a valid signed integrity-manifest record."
                )
                if not identity_matches:
                    verification_errors.append(f"{tag}: tag object or target commit differs from manifest")
            else:
                status = "unverified"
                mode = "none"
                detail = "Release tag has no trusted direct signature and is not an approved historical tag."
                verification_errors.append(f"{tag}: trusted direct signature required")
            observations.append(
                {
                    "tag": tag,
                    "tag_object_sha": tag_object,
                    "target_commit_sha": target_commit,
                    "status": status,
                    "assurance_mode": mode,
                    "detail": detail,
                }
            )

    missing = sorted(set(policy["legacy_attestation"]["permitted_unsigned_tags"]) - set(tags))
    verification_errors.extend(f"{tag}: approved historical tag is missing" for tag in missing)
    unverified = sorted(
        {item["tag"] for item in observations if item["status"] != "verified"} | set(missing)
    )
    return {
        "policy_id": policy["policy_id"],
        "policy_version": policy["schema_version"],
        "release_tags": tags,
        "tag_assessments": observations,
        "direct_verified_release_tags": [
            item["tag"] for item in observations
            if item["assurance_mode"] == "direct_signature_verified"
        ],
        "legacy_manifest_verified_tags": [
            item["tag"] for item in observations
            if item["assurance_mode"] == "legacy_manifest_verified"
        ],
        "unverified_release_tags": unverified,
        "verification_errors": sorted(set(verification_errors)),
        "future_tags_require_direct_signature": policy["cutover"][
            "future_tags_require_direct_signature"
        ],
    }
