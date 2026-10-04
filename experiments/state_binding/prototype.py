"""Private, single-ledger experiment. Fixture authority is never production consent."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from lib.result_ledger import canonical_digest
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.kernel import transaction_ref
from lib.governance_lifecycle.store import load_transactions, publish_transaction, writer_lock
from lib.governance_lifecycle.personal_probe import assess_bound_comments, replay_bound_snapshot

SCOPE = {"environment": "test_fixture", "repository": "synthetic/state-binding",
         "finding": "prototype-001", "contract": "1"}
SUBJECT = "test-person:owner"
PROFILE = {"id": "private-research", "version": "1"}
CHECKS = {"history", "state", "implementation", "head", "revision"}


class Rejected(ValueError):
    """A bounded experiment precondition failed; no publication is authorized."""


def need(condition, reason):
    if not condition:
        raise Rejected(reason)


def json_value(value):
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for item in value:
            json_value(item)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            json_value(item)
        return
    raise Rejected("unsupported_canonical_value")


def digest(value):
    json_value(value)
    return canonical_digest(value)


def raw_digest(raw):
    return hashlib.sha256(raw).hexdigest()


def no_symlinks(path):
    path = Path(path).absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)), "symlink_path")
    return path


def read_json(path):
    value = strict_json(no_symlinks(path).read_bytes())
    json_value(value)
    return value


def write_json(path, value):
    """Private mutable fixture/config write. Caller owns the ledger lock."""
    path = no_symlinks(path)
    json_value(value)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def workspace(path):
    root = no_symlinks(path)
    need(read_json(root / "EXPERIMENT.json") == SCOPE, "not_an_experiment_workspace")
    return root


def initialize(path):
    root = no_symlinks(path)
    resolved = root.resolve()
    if resolved.is_relative_to(REPO):
        need(any(resolved.is_relative_to(REPO / "experiments/state_binding" / p)
                 for p in ("runs", "human-demo")), "workspace_in_governed_repository_path")
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "EXPERIMENT.json", SCOPE)
    write_json(root / "provider.json", {})
    write_json(root / "executor-config.json", {"media_type": "text/plain"})
    (root / "ledger").mkdir()
    return root


def initial_state():
    return {"revision": 0, "latest_evidence": None, "publication": None,
            "role_binding": {"subject": SUBJECT, "active": True},
            "profile": deepcopy(PROFILE), "revoked_requests": []}


def history_payload(transactions):
    return {"commitment_type": "prototype-history", "version": "1", "scope": SCOPE,
            "transaction_count": len(transactions),
            "head_ref": transaction_ref(transactions[-1]) if transactions else None}


def state_payload(state):
    need(set(state) == set(initial_state()), "unexpected_state_fields")
    return {"commitment_type": "prototype-state", "version": "1", "scope": SCOPE,
            "state": deepcopy(state)}


def source_manifest():
    paths = list((REPO / "experiments/state_binding").glob("*.py"))
    paths += list((REPO / "scripts/lib/governance_lifecycle").glob("*.py"))
    paths += [REPO / name for name in ("scripts/lib/result_ledger.py", "scripts/lib/__init__.py",
              "requirements-validation.txt", "requirements-validation.lock", "scripts/validation-toolchain.env")]
    return {p.relative_to(REPO).as_posix(): raw_digest(no_symlinks(p).read_bytes())
            for p in sorted(paths)}


def implementation_manifest(root):
    return source_manifest() | {"workspace/executor-config.json":
                               raw_digest(no_symlinks(root / "executor-config.json").read_bytes())}


def implementation_payload(manifest):
    need(type(manifest) is dict and bool(manifest), "empty_implementation_manifest")
    for name, value in manifest.items():
        need(type(name) is str and not Path(name).is_absolute()
             and ".." not in Path(name).parts and "\\" not in name, "invalid_manifest_path")
        need(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
             "invalid_manifest_digest")
    return {"commitment_type": "prototype-implementation", "version": "1", "files": manifest}


def roots(transactions, state, manifest):
    return {"history": digest(history_payload(transactions)),
            "state": digest(state_payload(state)),
            "implementation": digest(implementation_payload(manifest))}


def validate_request(request):
    need(type(request) is dict and set(request) == {"version", "scope", "action", "roots",
         "implementation_manifest", "subject", "profile", "role_binding", "expected_head",
         "expected_sequence"}, "request_fields")
    need(request["version"] == "1" and request["scope"] == SCOPE, "request_version_or_scope")
    body = request["action"]
    need(type(body) is dict and set(body) == {"kind", "content"}, "action_fields")
    need(body["kind"] == "publish_test_artifact" and type(body["content"]) is str
         and 0 < len(body["content"].encode("utf-8")) <= 4096, "action_scope")
    need(type(request["expected_sequence"]) is int and request["expected_sequence"] >= 0,
         "request_sequence")
    need(type(request["roots"]) is dict and set(request["roots"]) == {"history", "state", "implementation"},
         "root_fields")
    need(request["roots"]["implementation"] == digest(implementation_payload(request["implementation_manifest"])),
         "implementation_manifest_binding")
    digest(request)


def preconditions(request, transactions, state, current_roots, *, omit=()):
    validate_request(request)
    need(set(omit) <= CHECKS, "unknown_ablation")
    need(request["subject"] == state["role_binding"]["subject"] and state["role_binding"]["active"]
         and request["role_binding"] == state["role_binding"], "role_changed")
    need(request["profile"] == state["profile"], "profile_changed")
    need(digest(request) not in state["revoked_requests"], "authorization_revoked")
    need(state["latest_evidence"] is not None, "evidence_missing")
    for key in ("history", "state", "implementation"):
        if key not in omit:
            need(request["roots"][key] == current_roots[key], "stale_" + key)
    if "head" not in omit:
        need(request["expected_head"] == history_payload(transactions)["head_ref"], "stale_head")
    if "revision" not in omit:
        need(request["expected_sequence"] == len(transactions), "stale_sequence")


def reduce_event(state, event):
    need(type(event) is dict and set(event) == {"kind", "body"}, "event_fields")
    kind, body = event["kind"], event["body"]
    value = deepcopy(state)
    if kind == "audit_note":
        need(type(body) is str and 0 < len(body) <= 1024, "note_body")
        return value
    if kind == "evidence":
        need(type(body) is dict and set(body) == {"run", "result"}
             and type(body["run"]) is str and body["result"] in ("pass", "fail"), "evidence_body")
        value["latest_evidence"] = deepcopy(body)
        value["publication"] = None
    elif kind == "role":
        need(type(body) is dict and set(body) == {"subject", "active"}
             and type(body["subject"]) is str and type(body["active"]) is bool, "role_body")
        value["role_binding"] = deepcopy(body)
        value["publication"] = None
    elif kind == "profile":
        need(type(body) is dict and set(body) == {"id", "version"}
             and all(type(v) is str for v in body.values()), "profile_body")
        value["profile"] = deepcopy(body)
        value["publication"] = None
    elif kind == "revoke":
        need(type(body) is dict and set(body) == {"request_digest", "subject", "environment"}
             and body["environment"] == "test_fixture" and body["subject"] == SUBJECT,
             "revocation_authority")
        target = body["request_digest"]
        need(type(target) is str and len(target) == 64 and all(c in "0123456789abcdef" for c in target),
             "revocation_target")
        need(target not in value["revoked_requests"], "already_revoked")
        value["revoked_requests"] = sorted([*value["revoked_requests"], target])
        if value["publication"] and value["publication"]["request_digest"] == target:
            value["publication"] = None
    elif kind == "publish":
        need(type(body) is dict and set(body) == {"request", "provider_statement", "manifest",
             "artifact", "omitted_checks", "human_capture"}, "publication_fields")
        statement = body["provider_statement"]
        validate_statement(body["request"], statement)
        if body["human_capture"] is not None:
            validate_human_capture(body["human_capture"], {"request": body["request"], "provider_statement": statement})
        artifact = body["artifact"]
        need(type(artifact) is dict and set(artifact) == {"content", "media_type"}
             and artifact["content"] == body["request"]["action"]["content"]
             and artifact["media_type"] in ("text/plain", "application/json"), "artifact_binding")
        value["publication"] = {"request_digest": digest(body["request"]), "artifact": deepcopy(artifact)}
    else:
        raise Rejected("unknown_event")
    value["revision"] += 1
    return value


def validate_statement(request, statement):
    need(type(statement) is dict and set(statement) == {"request_digest", "subject", "status",
         "environment", "revision"}, "provider_statement_fields")
    need(statement["environment"] == "test_fixture", "fixture_provider_required")
    need(statement["request_digest"] == digest(request) and statement["subject"] == request["subject"],
         "provider_content_binding")
    need(statement["status"] == "approved" and type(statement["revision"]) is int
         and statement["revision"] > 0, "provider_not_approved")


def validate_human_capture(capture, grant):
    """Offline consistency only; the human CLI separately fetches GitHub proof."""
    request = capture["request"]
    need(request["request_type"] == "private-prototype-local-demo"
         and request["prototype_grant"] == grant
         and request["repository_id"] == "joku-dev/devsecops-governance-framework",
         "human_request_binding")
    need(capture["capture_method"] == "github_api_get_via_gh", "human_provider_capture_method")
    result = replay_bound_snapshot(capture, assessor=assess_bound_comments)
    need(result["status"] == "confirmed", "human_statement_not_confirmed")


def replay(transactions):
    state, prefix = initial_state(), []
    for tx in transactions:
        need(type(tx) is dict and set(tx) == {"version", "scope", "sequence", "previous_ref",
             "event", "transaction_id"}, "transaction_fields")
        need(tx["version"] == "1" and tx["scope"] == SCOPE, "transaction_version_or_scope")
        need(type(tx["sequence"]) is int and tx["sequence"] == len(prefix) + 1, "transaction_sequence")
        need(tx["previous_ref"] == history_payload(prefix)["head_ref"], "broken_chain")
        payload = {k: v for k, v in tx.items() if k != "transaction_id"}
        need(tx["transaction_id"] == "transaction:" + digest(payload), "transaction_digest")
        if tx["event"]["kind"] == "publish":
            body = tx["event"]["body"]
            preconditions(body["request"], prefix, state, roots(prefix, state, body["manifest"]),
                          omit=body["omitted_checks"])
        state = reduce_event(state, tx["event"])
        prefix.append(tx)
    return state


def snapshot(root):
    transactions = load_transactions(workspace(root) / "ledger")
    state = replay(transactions)
    manifest = implementation_manifest(Path(root))
    return {"transactions": transactions, "state": state, "manifest": manifest,
            "roots": roots(transactions, state, manifest)}


def append_locked(root, history, event):
    state = replay(history)
    reduce_event(state, event)  # Validate before writing anything.
    tx = {"version": "1", "scope": SCOPE, "sequence": len(history) + 1,
          "previous_ref": history_payload(history)["head_ref"], "event": event}
    tx["transaction_id"] = "transaction:" + digest(tx)
    replay([*history, tx])
    publish_transaction(root / "ledger/transactions", tx)
    return tx


def record(root, kind, body):
    need(kind in ("evidence", "audit_note", "role", "profile"), "event_requires_authorization")
    root = workspace(root)
    with writer_lock(root / "ledger"):
        return append_locked(root, load_transactions(root / "ledger"), {"kind": kind, "body": deepcopy(body)})


def prepare(root, content="Bound experimental artifact"):
    root = workspace(root)
    with writer_lock(root / "ledger"):
        current = snapshot(root)
        request = {"version": "1", "scope": SCOPE,
                   "action": {"kind": "publish_test_artifact", "content": content},
                   "roots": current["roots"], "implementation_manifest": current["manifest"],
                   "subject": current["state"]["role_binding"]["subject"],
                   "profile": current["state"]["profile"], "role_binding": current["state"]["role_binding"],
                   "expected_sequence": len(current["transactions"]),
                   "expected_head": history_payload(current["transactions"])["head_ref"]}
        preconditions(request, current["transactions"], current["state"], current["roots"])
        return request


def fixture_approve(root, request):
    validate_request(request)
    root = workspace(root)
    statement = {"request_digest": digest(request), "subject": request["subject"],
                 "status": "approved", "environment": "test_fixture", "revision": 1}
    with writer_lock(root / "ledger"):
        provider = read_json(root / "provider.json")
        need(digest(request) not in provider, "fixture_statement_already_exists")
        provider[digest(request)] = statement
        write_json(root / "provider.json", provider)
    return {"request": deepcopy(request), "provider_statement": statement}


def update_fixture_provider(root, grant, disposition):
    root = workspace(root)
    need(disposition in ("revoked", "rejected", "edited", "deleted"), "fixture_disposition")
    with writer_lock(root / "ledger"):
        provider = read_json(root / "provider.json")
        key = digest(grant["request"])
        if disposition == "deleted":
            provider.pop(key, None)
        else:
            provider[key] = dict(grant["provider_statement"], status=disposition, revision=2)
        write_json(root / "provider.json", provider)


def execute(root, grant, *, omit=(), personal_verifier=None):
    """Ablation is a labelled research-only parameter, never a production bypass."""
    root = workspace(root)
    grant = deepcopy(grant)
    need(type(grant) is dict and set(grant) == {"request", "provider_statement"}, "grant_fields")
    request, retained = grant["request"], grant["provider_statement"]
    with writer_lock(root / "ledger"):
        current = snapshot(root)
        preconditions(request, current["transactions"], current["state"], current["roots"], omit=omit)
        validate_statement(request, retained)
        live = read_json(root / "provider.json").get(digest(request))
        need(live == retained, "provider_changed_or_missing")
        config = read_json(root / "executor-config.json")
        need(set(config) == {"media_type"} and config["media_type"] in ("text/plain", "application/json"),
             "executor_config")
        human_capture = personal_verifier(deepcopy(grant)) if personal_verifier is not None else None
        need(personal_verifier is None or human_capture is not None, "human_verifier_returned_no_proof")
        if human_capture is not None:
            need(not omit, "human_demo_cannot_ablate_checks")
            validate_human_capture(human_capture, grant)
        # A provider request may take time. Re-read the complete snapshot and
        # fixture provider before append; the lock remains held throughout.
        latest = snapshot(root)
        need(latest == current, "context_changed_during_provider_check")
        need(read_json(root / "provider.json").get(digest(request)) == retained,
             "provider_changed_during_check")
        event = {"kind": "publish", "body": {"request": request, "provider_statement": retained,
                 "manifest": current["manifest"], "omitted_checks": sorted(omit), "human_capture": human_capture,
                 "artifact": {"media_type": config["media_type"], "content": request["action"]["content"]}}}
        return append_locked(root, current["transactions"], event)


def revoke(root, grant):
    """Fixture correction remains possible after unrelated accepted changes."""
    root = workspace(root)
    with writer_lock(root / "ledger"):
        proof = read_json(root / "provider.json").get(digest(grant["request"]))
        need(proof is not None and proof["status"] == "revoked" and proof["subject"] == SUBJECT,
             "revocation_provider_required")
        return append_locked(root, load_transactions(root / "ledger"), {"kind": "revoke", "body": {
            "request_digest": digest(grant["request"]), "subject": SUBJECT, "environment": "test_fixture"}})
