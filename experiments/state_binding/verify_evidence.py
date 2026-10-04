"""Standalone read-only evidence verifier: standard library, no prototype imports."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

SCOPE = {"environment": "test_fixture", "repository": "synthetic/state-binding",
         "finding": "prototype-001", "contract": "1"}
SUBJECT = "test-person:owner"
EXPECTED = {"unchanged": "published", "new_evidence": "rejected", "audit_only_history": "rejected",
            "implementation_changed": "rejected", "role_changed": "rejected", "profile_changed": "rejected",
            "action_changed": "rejected", "provider_revoked": "rejected", "provider_edited": "rejected",
            "provider_deleted": "rejected", "state_root_changed": "rejected",
            "implementation_without_binding": "published", "history_without_history_root": "rejected",
            "history_without_history_preconditions": "published", "state_without_state_root": "published"}
OMISSIONS = {"implementation_without_binding": ["implementation"], "history_without_history_root": ["history"],
             "history_without_history_preconditions": ["history", "head", "revision"],
             "state_without_state_root": ["state"]}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def forbidden_number(value):
    raise ValueError("Floating point/non-finite numbers are outside contract 1")


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def load(path):
    check(path.is_file() and not path.is_symlink(), "Missing or symlink file")
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_float=forbidden_number, parse_constant=forbidden_number)


def h(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def ref(tx):
    return {"id": tx["transaction_id"], "digest": h(tx)}


def history_root(txs):
    return h({"commitment_type": "prototype-history", "version": "1", "scope": SCOPE,
              "transaction_count": len(txs), "head_ref": ref(txs[-1]) if txs else None})


def state_root(state):
    return h({"commitment_type": "prototype-state", "version": "1", "scope": SCOPE, "state": state})


def implementation_root(manifest):
    return h({"commitment_type": "prototype-implementation", "version": "1", "files": manifest})


def eligible(request, state, txs, manifest, statement, provider, omit=()):
    if request["version"] != "1" or request["scope"] != SCOPE:
        return False
    if request["roots"]["implementation"] != implementation_root(request["implementation_manifest"]):
        return False
    if request["subject"] != state["role_binding"]["subject"] or not state["role_binding"]["active"]:
        return False
    if request["role_binding"] != state["role_binding"] or request["profile"] != state["profile"]:
        return False
    if h(request) in state["revoked_requests"] or state["latest_evidence"] is None:
        return False
    current = {"history": history_root(txs), "state": state_root(state), "implementation": implementation_root(manifest)}
    if any(request["roots"][key] != root for key, root in current.items() if key not in omit):
        return False
    if "head" not in omit and request["expected_head"] != (ref(txs[-1]) if txs else None):
        return False
    if "revision" not in omit and request["expected_sequence"] != len(txs):
        return False
    return (statement == provider.get(h(request)) and statement["request_digest"] == h(request)
            and statement["subject"] == request["subject"] and statement["status"] == "approved"
            and statement["environment"] == "test_fixture")


def rebuild(txs):
    state = {"revision": 0, "latest_evidence": None, "publication": None,
             "role_binding": {"subject": SUBJECT, "active": True},
             "profile": {"id": "private-research", "version": "1"}, "revoked_requests": []}
    prefix = []
    for tx in txs:
        check(set(tx) == {"version", "scope", "sequence", "previous_ref", "event", "transaction_id"}, "Transaction fields")
        check(tx["version"] == "1" and tx["scope"] == SCOPE, "Transaction scope/version")
        check(type(tx["sequence"]) is int and tx["sequence"] == len(prefix) + 1, "Sequence")
        check(tx["previous_ref"] == (ref(prefix[-1]) if prefix else None), "Predecessor")
        check(tx["transaction_id"] == "transaction:" + h({k: v for k, v in tx.items() if k != "transaction_id"}), "Transaction digest")
        kind, body = tx["event"]["kind"], tx["event"]["body"]
        if kind == "evidence":
            state["latest_evidence"] = deepcopy(body)
            state["publication"] = None
        elif kind == "role":
            state["role_binding"] = deepcopy(body)
            state["publication"] = None
        elif kind == "profile":
            state["profile"] = deepcopy(body)
            state["publication"] = None
        elif kind == "revoke":
            check(body["subject"] == SUBJECT and body["environment"] == "test_fixture", "Revocation subject")
            check(body["request_digest"] not in state["revoked_requests"], "Repeated revocation")
            state["revoked_requests"] = sorted([*state["revoked_requests"], body["request_digest"]])
            if state["publication"] and state["publication"]["request_digest"] == body["request_digest"]:
                state["publication"] = None
        elif kind == "publish":
            check(body["human_capture"] is None, "Automated bundle cannot claim a human capture")
            request, statement = body["request"], body["provider_statement"]
            check(eligible(request, state, prefix, body["manifest"], statement, {h(request): statement},
                           body["omitted_checks"]), "Historical publication preconditions")
            check(body["artifact"]["content"] == request["action"]["content"], "Artifact/request binding")
            state["publication"] = {"request_digest": h(request), "artifact": deepcopy(body["artifact"])}
        else:
            check(kind == "audit_note" and type(body) is str, "Unknown event")
        if kind != "audit_note":
            state["revision"] += 1
        prefix.append(tx)
    return state


def verify_snapshot(path, source_manifest):
    snapshot = load(path / "snapshot.json")
    files = sorted((path / "transactions").glob("*.json"))
    txs = [load(p) for p in files]
    check(txs == snapshot["transactions"], "Stored snapshot differs from actual transaction files")
    for file, tx in zip(files, txs):
        check(file.name == f"{tx['sequence']:08d}-{tx['transaction_id'].split(':')[1]}.json", "Transaction filename")
    state = rebuild(txs)
    check(state == snapshot["state"], "Projection mismatch")
    check(load(path / "EXPERIMENT.json") == SCOPE, "Workspace marker")
    config_sha = hashlib.sha256((path / "executor-config.json").read_bytes()).hexdigest()
    check(snapshot["manifest"] == source_manifest | {"workspace/executor-config.json": config_sha}, "Implementation inventory")
    check(snapshot["roots"] == {"history": history_root(txs), "state": state_root(state),
                               "implementation": implementation_root(snapshot["manifest"])}, "Root projection mismatch")
    return snapshot


def verify_directory(root, expected_digest=None):
    check(not root.is_symlink(), "Symlink bundle directory")
    manifest_path = root / "MANIFEST.json"
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if expected_digest is not None:
        check(manifest_sha == expected_digest, "External manifest anchor mismatch")
    manifest = load(manifest_path)
    check(manifest["contract"] == "1" and manifest["classification"] == "confidential_test_evidence", "Manifest contract")
    actual = set()
    for path in root.rglob("*"):
        check(not path.is_symlink(), "Symlink in bundle")
        if path.is_file() and path != manifest_path:
            actual.add(path.relative_to(root).as_posix())
    check(actual == set(manifest["files"]), "Bundle file inventory mismatch")
    for name, sha in manifest["files"].items():
        check(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts, "Unsafe bundle path")
        check(hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, "Checksum mismatch: " + name)
    report = load(root / "results.json")
    check(report["official_state"] is False and report["human_authorization_proven"] is False
          and report["patentability_assessed"] is False, "Evidence classification")
    special = {"retry", "revocation_after_change", "concurrent_publication"}
    indexed = {r["id"]: r for r in report["results"]}
    check(len(indexed) == len(report["results"]) and set(indexed) == set(EXPECTED) | special, "Experiment inventory")
    for name, result in indexed.items():
        case = root / "cases" / name
        check(load(case / "result.json") == result, "Result index mismatch")
        before = verify_snapshot(case / "before", report["source_manifest"])
        after = verify_snapshot(case / "after", report["source_manifest"])
        if (case / "prepared").exists():
            prepared = verify_snapshot(case / "prepared", report["source_manifest"])
            if name == "audit_only_history":
                check(prepared["roots"]["state"] == before["roots"]["state"]
                      and prepared["roots"]["history"] != before["roots"]["history"], "History/state distinction")
        for file in (case / "before/transactions").glob("*.json"):
            check(file.read_bytes() == (case / "after/transactions" / file.name).read_bytes(), "Immutable prefix changed")
        grant = load(case / "grant.json")
        delta = len(after["transactions"]) - len(before["transactions"])
        check(delta == result["transaction_delta"], "Reported write effect differs")
        if name in EXPECTED:
            omit = OMISSIONS.get(name, [])
            check(result["omitted_checks"] == omit and result["expected"] == EXPECTED[name], "Scenario contract differs")
            allowed = eligible(grant["request"], before["state"], before["transactions"], before["manifest"],
                               grant["provider_statement"], load(case / "before/provider.json"), omit)
            expected = "published" if allowed else "rejected"
            check(expected == result["outcome"] == EXPECTED[name], "Independently evaluated result differs")
            check(delta == int(allowed), "Unauthorized or missing write")
            if allowed:
                event = after["transactions"][-1]["event"]
                check(event["kind"] == "publish" and event["body"]["request"] == grant["request"], "Publication request")
                check(event["body"]["artifact"]["media_type"] == load(case / "before/executor-config.json")["media_type"], "Execution configuration")
        else:
            check(sorted(a["outcome"] for a in result["attempts"]) == ["published", "rejected"], "Duplicate/concurrency outcomes")
            if name == "concurrent_publication":
                check(len({a["process_id"] for a in result["attempts"]}) == 2, "Distinct process evidence missing")
            added = after["transactions"][len(before["transactions"]):]
            check(sum(t["event"]["kind"] == "publish" for t in added) == 1, "Duplicate publication effect")
            check(delta == (3 if name == "revocation_after_change" else 1), "Unexpected appended records")
            if name == "revocation_after_change":
                check(after["state"]["publication"] is None and h(grant["request"]) in after["state"]["revoked_requests"], "Revocation projection")
                check(load(case / "correction.json") == added[-1], "Correction evidence")
                check(load(case / "after/provider.json")[h(grant["request"])]["status"] == "revoked", "Revocation provider")
        check(result["passed"] is True, "Experiment failed")
    if report["comparison"] is not None:
        for run in report["comparison"]["runs"]:
            log = (root / run["log"]).read_text()
            check(run["returncode"] == 0 and "\nOK\n" in log and "Ran " in log, "Existing pilot regression failed")
    check(report["passed"] is True, "Bundle did not pass")
    return {"verified": True, "experiments": len(indexed), "bundle_manifest_sha256": manifest_sha,
            "external_anchor_checked": expected_digest is not None, "human_authorization_proven": False}


def verify(path, expected_digest=None):
    path = Path(path)
    if path.is_dir():
        return verify_directory(path, expected_digest)
    with tempfile.TemporaryDirectory(prefix="state-binding-verify-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(path) as archive:
            names = set()
            total = 0
            for info in archive.infolist():
                parts = PurePosixPath(info.filename)
                check(not parts.is_absolute() and ".." not in parts.parts and "\\" not in info.filename,
                      "Unsafe archive path")
                check(info.filename not in names and not info.is_dir(), "Duplicate/directory archive member")
                check((info.external_attr >> 16) & 0o170000 != 0o120000, "Archive symlink")
                names.add(info.filename)
                total += info.file_size
                check(total <= 25_000_000 and len(names) <= 2000, "Archive exceeds experiment bounds")
                dest = root / parts
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(info))
        return verify_directory(root, expected_digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.expect_manifest_sha256)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"verified": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
