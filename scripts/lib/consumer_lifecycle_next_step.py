"""Read-only, evidence-bound guidance for the next consumer lifecycle operation."""
from pathlib import Path
import json

from .governance_lifecycle.consumer_acceptance import INDEX, projection as acceptance_projection
from .governance_lifecycle.consumer_actions import load_context, project_actions, state_at


CENTRAL = "https://github.com/joku-dev/devsecops-governance-framework"
CONSUMER = "https://github.com/joku-dev/governance-framework-demo-consumer"
INDEX_PATH = "status/governance-consumer-lifecycle.json"
GUIDE_PATH = "docs/operations/evidence/consumer-lifecycle-operation.md"
UPDATE_WORKFLOW = f"{CENTRAL}/actions/workflows/consumer-lifecycle-update.yml"
ARCHITECTURE_WORKFLOW = f"{CONSUMER}/actions/workflows/architecture-baseline-l1-v0.1.0.yml"


def _transaction_path(kind, transaction):
    digest = transaction["transaction_id"].split(":", 1)[1]
    sequence = transaction["sequence"]
    ledger = "observations" if kind == "observation" else "actions"
    return f"governance/consumer-lifecycle/{ledger}/transactions/{sequence:08d}-{digest}.json"


def _transaction_url(kind, transaction):
    return f"{CENTRAL}/blob/main/{_transaction_path(kind, transaction)}"


def _action_links(action):
    request = action["request"]
    links = [{"label": "Aktionsnachweis", "url": _transaction_url("action", action)}]
    discussion = request.get("discussion_number")
    if type(discussion) is int:
        links.insert(0, {
            "label": f"Persönliche Erklärung · PR #{discussion}",
            "url": f"{CENTRAL}/pull/{discussion}",
        })
    return links


def _receipt_links(receipt):
    source = receipt["source"]
    run_id = source.get("run_id")
    links = [{"label": "Beleg im Ledger", "url": _transaction_url("observation", receipt)}]
    if type(run_id) is int or (isinstance(run_id, str) and run_id.isdigit()):
        links.insert(0, {"label": f"Consumer-Lauf {run_id}", "url": f"{CONSUMER}/actions/runs/{run_id}"})
    return links


def _current_step(index, receipts, actions, state, candidate):
    common = [
        {"label": "Consumer-Betriebsleitfaden", "url": f"{CENTRAL}/blob/main/{GUIDE_PATH}"},
        {"label": "Lifecycle-Update-Workflow", "url": UPDATE_WORKFLOW},
    ]
    if not index.get("official_state") or not index.get("operating_acceptance", {}).get("effective"):
        return {
            "id": "acceptance_required", "title": "Betriebsabnahme prüfen",
            "detail": "Die separate Consumer-Betriebsabnahme ist nicht wirksam. Vor neuen Lifecycle-Aktionen muss der versionierte Annahmeweg geprüft werden.",
            "operation": "acceptance", "links": common,
        }
    if not state.get("roles_active"):
        return {
            "id": "roles_inactive", "title": "Rollenstatus klären",
            "detail": "Die bestätigten Consumer-Rollen sind zurückgezogen. Neue Entscheidungen oder Abschlüsse sind bis zu einer gültigen versionierten Rollenklärung nicht möglich.",
            "operation": "acceptance", "links": common,
        }
    if candidate["finding_state"] == "needs_clarification" or candidate["counts"]["quarantined"]:
        return {
            "id": "resolve_clarification", "title": "Evidenzkonflikt klären",
            "detail": "Mindestens ein Eingang ist quarantänisiert. Erst nach Klärung darf der Lifecycle fortgesetzt werden.",
            "operation": None, "links": common,
        }
    if state.get("closure"):
        return {
            "id": "closed_wait", "title": "Kein offener Schritt",
            "detail": "Das Finding ist geschlossen. Es gibt keine ausstehende Maßnahme. Der manuelle Pilot überwacht nicht kontinuierlich; erst eine neue zulässige Fehlerbeobachtung kann den Fall wieder öffnen.",
            "operation": None, "links": common,
        }

    failures = [r for r in receipts if r["outcome"] == "eligible_for_pilot" and r["criterion"]["status"] == "fail"]
    if not failures:
        return {
            "id": "wait_for_failure", "title": "Kein offener Fehlerfall",
            "detail": "Es liegt kein akzeptierter Fehler vor, der eine Behebungsentscheidung begründet. Bei einer neuen Beobachtung zuerst einen zulässigen Mainline-Lauf erfassen.",
            "operation": None, "links": common + [{"label": "Architektur-Workflow im Consumer", "url": ARCHITECTURE_WORKFLOW}],
        }

    latest_failure = max(failures, key=lambda r: (r["source"]["observed_at"], r["transaction_id"]))
    failure_links = _receipt_links(latest_failure)
    if state.get("decision") is None:
        return {
            "id": "decision_required", "title": "Behebungsentscheidung vorbereiten",
            "detail": "Der aktuelle offene Fehler braucht eine eigene, evidenz- und revisionsgebundene Entscheidung. Vor Zustimmung muss die Fehlerbeobachtung innerhalb der dokumentierten Frischegrenze liegen.",
            "operation": "action", "links": failure_links + common,
        }

    decision_links = _action_links(state["decision"])
    progress = state.get("progress")
    if progress is None:
        return {
            "id": "in_progress_required", "title": "Fortschritt persönlich erfassen",
            "detail": "Die Behebungsentscheidung ist aktiv. Der nächste Lifecycle-Schritt ist eine separate persönliche `in_progress`-Erklärung mit dem konkreten Arbeitsnachweis.",
            "operation": "action", "links": decision_links + failure_links + common,
        }
    progress_value = progress["request"]["body"].get("progress")
    progress_links = _action_links(progress)
    if progress_value == "in_progress":
        return {
            "id": "completed_required", "title": "Abgeschlossene Arbeit erfassen",
            "detail": "Der Fortschritt ist als `in_progress` erfasst. Nach belegtem Abschluss ist die eigene persönliche `completed`-Erklärung erforderlich.",
            "operation": "action", "links": progress_links + decision_links + common,
        }

    if progress_value == "completed":
        latest = max(receipts, key=lambda r: (r["source"]["observed_at"], r["transaction_id"]))
        pass_after_completion = (
            latest["outcome"] == "eligible_for_pilot"
            and latest["criterion"]["status"] == "pass"
            and latest["source"]["observed_at"] >= progress["recorded_at"]
            and all(r["source"]["observed_at"] < latest["source"]["observed_at"] for r in failures)
        )
        if not pass_after_completion:
            return {
                "id": "fresh_pass_required", "title": "Frischen Mainline-PASS erfassen",
                "detail": "Nach `completed` ist noch kein passender neuester Mainline-PASS nachgewiesen. Einen erfolgreichen ersten `push`-Lauf auf `main` ausführen und anschließend als Observation aufnehmen.",
                "operation": "observe", "links": progress_links + failure_links + common + [
                    {"label": "Architektur-Workflow im Consumer", "url": ARCHITECTURE_WORKFLOW}],
            }
        return {
            "id": "closure_required", "title": "Abschlussentscheidung vorbereiten",
            "detail": "Ein zulässiger PASS nach der abgeschlossenen Arbeit liegt vor. Der Abschluss braucht weiterhin eine separate persönliche Zustimmung; der Intake prüft Evidenzfrische und vollständige Reihenfolge erneut.",
            "operation": "action", "links": _receipt_links(latest) + progress_links + decision_links + common,
        }

    return {
        "id": "inspect_state", "title": "Lifecycle-Zustand prüfen",
        "detail": "Der gespeicherte Fortschritt entspricht keiner bekannten Lifecycle-Stufe. Keine automatische Aktion wird empfohlen; den Index und die Transaktionshistorie prüfen.",
        "operation": "refresh", "links": common + [{"label": "Offizieller Statusindex", "url": f"{CENTRAL}/blob/main/{INDEX_PATH}"}],
    }


def build(root: Path):
    root = Path(root)
    index = json.loads((root / INDEX).read_text(encoding="utf-8"))
    expected = acceptance_projection(root)
    if index != expected:
        raise ValueError("Consumer lifecycle index differs from its validated ledger projection")
    if index.get("scope", {}).get("repository_id") != "joku-dev/governance-framework-demo-consumer" or index.get("scope", {}).get("rule_id") != "operation_readiness":
        raise ValueError("Consumer lifecycle scope differs from the read-only viewer profile")

    _profile, _binding, receipts, actions = load_context(root)
    candidate = project_actions(root)
    state = state_at(receipts, actions)
    next_step = _current_step(index, receipts, actions, state, candidate)

    history = []
    for receipt in receipts:
        history.append({
            "recorded_at": receipt["recorded_at"],
            "kind": "Observation",
            "status": receipt["criterion"]["status"],
            "detail": f"{receipt['criterion']['id']} · Versuch {receipt['source']['run_attempt']}",
            "links": _receipt_links(receipt),
        })
    for action in actions:
        body = action["request"]["body"]
        detail = body.get("progress") or body["kind"]
        history.append({
            "recorded_at": action["recorded_at"],
            "kind": "Aktion",
            "status": action["outcome"],
            "detail": detail,
            "links": _action_links(action),
        })
    history.sort(key=lambda item: (item["recorded_at"], item["kind"]))

    return {
        "scope": index["scope"],
        "finding_state": index["finding_state"],
        "official_state": index["official_state"],
        "enforcement": index["enforcement"],
        "as_of": index["as_of"],
        "counts": index["counts"],
        "next_step": next_step,
        "source_url": f"{CENTRAL}/blob/main/{INDEX_PATH}",
        "history": history,
    }
