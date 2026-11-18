"""Durable, reproducible pilot eligibility receipts; operational activation is separate."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile

from .adapter import json_bytes, strict_json
from .contracts import ROOT, canonical_digest, finding_id, require, schema_validator, timestamp
from .kernel import transaction_ref
from .live_evidence import collect_preflight, replay_capture
from .live_preparation import revision_ref, validate_preparation
from .store import load_transactions, publish_transaction, writer_lock

OPERATING_PATH = "model/governance/lifecycle/live-operating"
VALIDATION_LEDGER = "governance/lifecycle/live-validation"
MAX_CAPTURE_BYTES = 25 * 1024 * 1024


def load_operating(repo=ROOT):
    root = Path(repo)
    directory = root / OPERATING_PATH
    require(directory.is_dir() and not directory.is_symlink() and {p.name for p in directory.iterdir()} == {"00000001.json"}, "Unexpected operating profile revision")
    require(not (directory / "00000001.json").is_symlink(), "Operating profile must not be a symlink")
    profile = strict_json((directory / "00000001.json").read_bytes())
    schema_validator("pilot-operating").validate(profile)
    prepared = validate_preparation(root)
    require(profile["preparation_ref"] == revision_ref(prepared["profile"]), "Operating preparation revision differs")
    require(profile["role_binding_ref"] == revision_ref(prepared["binding"]), "Operating role revision differs")
    require(prepared["assignments"], "Pilot appointments are withdrawn")
    return profile


def capture_files(directory):
    result = replay_capture(directory)
    root = Path(directory)
    files = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    require(sum(map(len, files.values())) <= MAX_CAPTURE_BYTES, "Capture exceeds supported size")
    return result, files


def replay_embedded(encoded):
    require(type(encoded) is dict and bool(encoded), "Complete capture is required")
    files = {}
    for name, data in encoded.items():
        path = Path(name)
        require(type(name) is str and not path.is_absolute() and ".." not in path.parts and str(path) == name,
                "Unsafe capture member")
        require(type(data) is str and len(data) <= MAX_CAPTURE_BYTES * 2, "Unsupported capture encoding")
        files[name] = base64.b64decode(data, validate=True)
    require(sum(map(len, files.values())) <= MAX_CAPTURE_BYTES, "Capture exceeds supported size")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name, data in files.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return replay_capture(root)


def origin_key(capture):
    source = capture["source"]
    return canonical_digest({"repository_id":capture["repository_id"], "commit_id":source["commit_id"],
        "run_id":source["run_id"], "run_attempt":source["run_attempt"], "workflow_id":source["workflow_id"],
        "workflow_path":source["workflow_path"], "artifact_name":"governance-repository-security",
        "rule_id":"GRS-002", "resource":"refs/heads/main"})


def producer_fingerprint(capture):
    source = capture["source"]
    return canonical_digest({k:source[k] for k in ("artifact_id", "artifact_sha256", "report_sha256",
        "observed_at", "source_profile_version", "verified_file_digests")})


def prepare_receipt(capture, encoded, profile, history, *, recorded_at, expected_sequence):
    schema_validator("pilot-operating").validate(profile)
    require(capture["profile_ref"] == profile["preparation_ref"], "Capture preparation differs")
    key, digest = origin_key(capture), producer_fingerprint(capture)
    prior = next((t for t in history if t["origin_key"] == key), None)
    reason = "producer_conflict" if prior else "verified_capture_within_operating_policy"
    if prior is None:
        prior = next((t for t in history if t["outcome"] == "eligible_for_pilot"
            and t["source"]["observed_at"] == capture["source"]["observed_at"]
            and t["criterion"]["status"] != capture["criterion"]["status"]), None)
        if prior:
            reason = "ambiguous_time"
    # Exact redelivery does not create new acceptance, even after evidence ages.
    if any(t["origin_key"] == key and t["producer_fingerprint"] == digest for t in history):
        return None
    require(type(expected_sequence) is int and expected_sequence == len(history), "Stale receipt sequence")
    age = (timestamp(recorded_at) - timestamp(capture["source"]["observed_at"])).total_seconds()
    require(timestamp(capture["captured_at"]) <= timestamp(recorded_at), "Receipt predates capture")
    require(0 <= age <= profile["operating_policy"]["maximum_age_seconds"], "Evidence is future-dated or stale")
    require(not history or timestamp(recorded_at) >= timestamp(history[-1]["recorded_at"]), "Receipt clock regressed")
    receipt = {"schema_version":"0.1.0", "record_type":"lifecycle-pilot-eligibility-receipt",
        "environment":"live_pilot_validation", "official_state":False, "live_activation_approved":False,
        "sequence":len(history)+1, "previous_ref":transaction_ref(history[-1]) if history else None,
        "profile_ref":revision_ref(profile), "recorded_at":recorded_at, "expected_sequence":expected_sequence,
        "origin_key":key, "producer_fingerprint":digest,
        "outcome":"quarantined" if prior else "eligible_for_pilot",
        "reason":reason,
        "conflicts_with":transaction_ref(prior) if prior else None,
        "provider_authentication":"new_receipt_requires_independent_PR_check",
        "capture":deepcopy(encoded), "criterion":deepcopy(capture["criterion"]),
        "source":deepcopy(capture["source"]), "age_seconds_at_receipt":int(age)}
    receipt["transaction_id"] = "transaction:" + canonical_digest(receipt)
    schema_validator("pilot-receipt").validate(receipt)
    return receipt


def replay_receipts(transactions, profile):
    history = []
    for transaction in transactions:
        schema_validator("pilot-receipt").validate(transaction)
        capture = replay_embedded(transaction["capture"])
        expected = prepare_receipt(capture, transaction["capture"], profile, history,
            recorded_at=transaction["recorded_at"], expected_sequence=transaction["expected_sequence"])
        require(expected is not None and transaction == expected, "Receipt chain or eligibility proof differs")
        history.append(transaction)
    return history


def append_capture(root, directory, profile, *, recorded_at, expected_sequence):
    capture, files = capture_files(directory)
    encoded = {p:base64.b64encode(b).decode("ascii") for p,b in sorted(files.items())}
    with writer_lock(root):
        history = replay_receipts(load_transactions(root), profile)
        receipt = prepare_receipt(capture, encoded, profile, history,
            recorded_at=recorded_at, expected_sequence=expected_sequence)
        if receipt is None:
            return {"outcome":"duplicate", "transaction_ref":None}
        publish_transaction(Path(root) / "transactions", receipt)
        return {"outcome":receipt["outcome"], "transaction_ref":transaction_ref(receipt)}


def project_receipts(transactions, profile):
    history = replay_receipts(transactions, profile)
    eligible = [t for t in history if t["outcome"] == "eligible_for_pilot"]
    conflicts = [t for t in history if t["outcome"] == "quarantined"]
    failures = [t for t in eligible if t["criterion"]["status"] == "fail"]
    latest = max(eligible, key=lambda t:(t["source"]["observed_at"],t["transaction_id"])) if eligible else None
    key = {"repository_id":profile["scope"]["repository_id"], "domain":"governance_repository_security",
           "rule_id":"GRS-002", "finding_type":"criterion_failure", "resource":"refs/heads/main"}
    return {"schema_version":"0.1.0", "index_type":"lifecycle-live-pilot-validation", "official_state":False,
        "live_activation_approved":False, "enforcement":"report_only", "profile_ref":revision_ref(profile),
        "as_of":history[-1]["recorded_at"] if history else None,
        "head_ref":transaction_ref(history[-1]) if history else None,
        "counts":{"receipts":len(history), "eligible":len(eligible), "quarantined":len(conflicts), "failures":len(failures)},
        "latest_criterion_result":latest["criterion"]["status"] if latest else None,
        "pilot_finding":({"finding_id":finding_id(key), "state":"needs_clarification" if conflicts else "open",
            "occurrences":len(failures), "closure_supported":False} if failures else None),
        "receipt_refs":[transaction_ref(t) for t in history],
        "limitation":"Eligibility validation only; personal decisions and LD-07 are required before operational lifecycle use"}


def verify_new_receipts(repo, base_ref):
    """Required PR check: obtain fresh provider bytes instead of trusting persisted claims."""
    root = Path(repo); profile = load_operating(root)
    old = set(subprocess.check_output(["git","ls-tree","-r","--name-only",base_ref,"--",VALIDATION_LEDGER],cwd=root,text=True).splitlines())
    checked = 0
    for path in sorted((root / VALIDATION_LEDGER / "transactions").glob("*.json")):
        if str(path.relative_to(root)) in old:
            continue
        receipt = strict_json(path.read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            observed = collect_preflight(str(receipt["source"]["run_id"]), Path(temporary)/"capture", repo_root=root)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
        require(origin_key(observed) == receipt["origin_key"] and producer_fingerprint(observed) == receipt["producer_fingerprint"],
                "New receipt differs from independently retrieved GitHub evidence")
        age = (timestamp(now)-timestamp(observed["source"]["observed_at"])).total_seconds()
        require(0 <= age <= profile["operating_policy"]["maximum_age_seconds"], "New receipt is stale at PR acceptance")
        require(timestamp(receipt["recorded_at"]) <= timestamp(now), "Receipt claims a future acceptance time")
        checked += 1
    return checked
