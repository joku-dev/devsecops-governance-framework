#!/usr/bin/env python3
"""Generate a deterministic index for explicit evidence-agent provenance."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
RECORD_ROOT = ROOT / "status" / "evidence-agent-provenance"
INDEX_PATH = ROOT / "status" / "evidence-agent-provenance-index.json"


def main() -> int:
    records = []
    if RECORD_ROOT.exists():
        for path in sorted(RECORD_ROOT.rglob("*.json")):
            records.append(json.loads(path.read_text(encoding="utf-8")))
    records.sort(key=lambda item: (item.get("recorded_at", ""), item.get("provenance_id", "")))
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "record_count": len(records),
            "agent_counts": dict(sorted(Counter(item.get("agent", {}).get("id", "unknown") for item in records).items())),
            "involvement_counts": dict(sorted(Counter(item.get("involvement", "unknown") for item in records).items())),
        },
        "records": records,
    }
    INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
