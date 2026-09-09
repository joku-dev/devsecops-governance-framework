#!/usr/bin/env python3
"""Create a public-neutral candidate mapping without publishing source text."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import yaml


ROOT = Path(__file__).resolve().parents[1]
XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"m": XML_NS}

STANDARD_ALIASES = {
    "BSI_IT_Grundschutz": ("BSI-IT-GRUNDSCHUTZ", "BSI IT-Grundschutz"),
    "BSI-TR-03183-1": ("BSI-TR-03183-1", "BSI TR-03183-1"),
    "BSI-TR-03183-2": ("BSI-TR-03183-2", "BSI TR-03183-2"),
    "BWI Software Engineering Framework": ("BWI-SEF-2025", "BWI Software Engineering Framework 2025"),
    "IEC62443_4_1": ("IEC-62443-4-1", "IEC 62443-4-1"),
    "NIST800-218": ("NIST-SP-800-218", "NIST SP 800-218"),
    "OWASP_ASVS": ("OWASP-ASVS", "OWASP ASVS"),
    "OWASP_TOP_10_2025": ("OWASP-TOP-10-2025", "OWASP Top 10 2025"),
    "Internal Application Security Standard (Sanitized)": ("PRIVATE-APPSEC-SANITIZED", "Private application security source (sanitized)"),
    "Internal Information Security Standard (Sanitized)": ("PRIVATE-INFOSEC-SANITIZED", "Private information security source (sanitized)"),
    "Internal Software Security Standard (Sanitized)": ("PRIVATE-SWSEC-SANITIZED", "Private software security source (sanitized)"),
}

EXACT_SOURCE_ID_MAP = {
    ("IEC-62443-4-1", "SM-6"): ["HREQ-SC-003"],
    ("IEC-62443-4-1", "SM-7"): ["HREQ-DEV-004"],
    ("IEC-62443-4-1", "SM-8"): ["HREQ-SC-004"],
    ("IEC-62443-4-1", "SM-9"): ["HREQ-DEV-005"],
    ("IEC-62443-4-1", "SM-10"): ["HREQ-DEV-005"],
    ("IEC-62443-4-1", "SM-11"): ["HREQ-OPS-002"],
    ("IEC-62443-4-1", "SD-3"): ["HREQ-RISK-004"],
    ("IEC-62443-4-1", "SI-1"): ["HREQ-DEV-003"],
    ("IEC-62443-4-1", "SI-2"): ["HREQ-DEV-002"],
    ("IEC-62443-4-1", "SVV-1"): ["HREQ-TEST-003"],
    ("IEC-62443-4-1", "SVV-3"): ["HREQ-TEST-004"],
    ("IEC-62443-4-1", "SVV-4"): ["HREQ-TEST-005"],
    ("IEC-62443-4-1", "SVV-5"): ["HREQ-TEST-006"],
    ("IEC-62443-4-1", "SUM-1"): ["HREQ-OPS-003"],
    ("IEC-62443-4-1", "SUM-4"): ["HREQ-OPS-003"],
    ("IEC-62443-4-1", "SG-1"): ["HREQ-RISK-004"],
    ("IEC-62443-4-1", "SG-2"): ["HREQ-RISK-004"],
    ("IEC-62443-4-1", "SG-3"): ["HREQ-APP-007", "HREQ-OPS-006"],
    ("IEC-62443-4-1", "SG-4"): ["HREQ-OPS-007"],
    ("IEC-62443-4-1", "SG-5"): ["HREQ-OPS-006"],
    ("IEC-62443-4-1", "SG-6"): ["HREQ-APP-001"],
}

CONTENT_RULES = [
    ("HREQ-SC-010", r"licen[cs]e compliance|licen[cs]e approval|distribution licen[cs]e|usage licen[cs]e"),
    ("HREQ-SC-009", r"spdx|licen[cs]e identifier|licen[cs]e expression|licen[cs]e list|licen[cs]e metadata"),
    ("HREQ-SC-008", r"component.*(?:hash|checksum|source|uri|url|purl|cpe)|(?:hash|checksum|source uri|package url).*(?:component|sbom)"),
    ("HREQ-SC-007", r"component (?:creator|name|version)|dependency relationship|depends on|contains.*component|filename|structured property|archive property|executable property"),
    ("HREQ-SC-006", r"\bsbom\b|software bill of materials|component inventory"),
    ("HREQ-RISK-001", r"identify all assets|identify threats|likelihood.*impact|impact.*likelihood|risk analysis|risk assessment"),
    ("HREQ-RISK-002", r"threat model|bedrohungsmodell"),
    ("HREQ-RISK-003", r"risk treatment|risk reassess|update the risk assessment|control effectiveness|effectiveness and correctness|accept.*risk"),
    ("HREQ-RISK-004", r"security architecture|architecture review|design review|defen[cs]e in depth|trust boundar"),
    ("HREQ-TEST-005", r"penetration.?test"),
    ("HREQ-TEST-006", r"independen.*test|test.*independen|test environment.*production|anonymi[sz].*test data|test personnel"),
    ("HREQ-TEST-001", r"test plan|acceptance plan|abnahmeplan|test planning|planung der software-tests|release acceptance"),
    ("HREQ-TEST-002", r"regression test|functional test|non.functional|performance|test plan|software test|nachtest|unit test|integration test"),
    ("HREQ-TEST-003", r"security requirement.*test|security test|negative test|verify.*security requirement|critical flow"),
    ("HREQ-TEST-004", r"vulnerability test|vulnerability scan|vulnerability assessment|dynamic analysis"),
    ("HREQ-DEV-003", r"code review|implementation review|static analysis|human.readable code|review process.*code|review process.*configuration"),
    ("HREQ-DEV-002", r"secure coding|coding standard"),
    ("HREQ-DEV-004", r"development environment|entwicklungsumgebung"),
    ("HREQ-DEV-005", r"external component|extern.*bibliothek|third.party supplier|supplier|secure acquisition"),
    ("HREQ-DEV-001", r"version control|versionsverwaltung|source code.*integrity|protect.*code|branch"),
    ("HREQ-APP-002", r"session management|session identifier|session timeout|session invalid"),
    ("HREQ-APP-005", r"file upload|file download|file handling"),
    ("HREQ-APP-004", r"input validation|output encoding|business logic|validation logic"),
    ("HREQ-APP-001", r"authentication|authorization|access control|account management|least privilege"),
    ("HREQ-APP-003", r"sensitive data|data protection|encryption|cryptographic|kryptograf|retention|privacy|anonym"),
    ("HREQ-APP-006", r"security log|logging|alerting|error handling|exception|information leakage"),
    ("HREQ-APP-007", r"secure default|hardening|security configuration|misconfiguration|web application firewall|sandbox|containeri[sz]"),
    ("HREQ-SC-004", r"artifact.*sign|component.*sign|signing key|private key|key management|cryptographic sign"),
    ("HREQ-SC-005", r"dependency provenance|trusted repositor|trusted source|dependency source"),
    ("HREQ-SC-002", r"reproducible build|isolated build|recreate.*build environment|multi.stage build|runtime image"),
    ("HREQ-SC-003", r"artifact integrity|file integrity|artifact.*checksum|artifact.*digest|unique.*artifact"),
    ("HREQ-SC-001", r"build process|build pipeline|compilation|build configuration|automated build"),
    ("HREQ-OPS-003", r"security update|patch management|patch- und |update delivery|update qualification|autoupdate|change management|änderungsmanagement"),
    ("HREQ-OPS-002", r"remediat.*vulnerab|address.*security.*issue|vulnerability management|risk.based timeline"),
    ("HREQ-OPS-004", r"siem|security event|monitoring|monitor|alarm|alert|log protection|user interaction"),
    ("HREQ-OPS-005", r"installation.*verification|deployment.*configuration|configuration baseline|configuration management test"),
    ("HREQ-OPS-006", r"secure operation|operation guideline|installation guidance|administration guidance|recovery guidance"),
    ("HREQ-OPS-007", r"decommission|disposal|deinstall|secure deletion|key destruction|außer betrieb"),
    ("HREQ-OPS-008", r"vulnerability disclosure|security health|health check|security response|re.accredit"),
    ("HREQ-OPS-001", r"release approval|security gate|acceptance plan|software release|freigabe"),
    ("HREQ-APP-001", r"central.*identity|multi.factor|privileged access|role.based"),
    ("HREQ-OPS-005", r"infrastructure as code|infrastructure definition"),
    ("HREQ-GOV-004", r"machine.readable evidence|compliance evidence|audit evidence|traceab|requirements.*source.*test|source.*build.*deploy"),
    ("HREQ-SC-003", r"runtime.*integrity|deployed.*integrity"),
    ("HREQ-GOV-003", r"responsibilit|competence|qualification|training|personnel|zuständig|fachverantwort|security cleared|supervised"),
    ("HREQ-GOV-004", r"documentation|documented|dokumentation|uml model|concept of operations|conops|secops"),
    ("HREQ-GOV-002", r"security level|criticality|applicability|risk.based application|security requirement|security language|sicherheitsanforder"),
    ("HREQ-GOV-001", r"lifecycle|development process|vorgehensmodell|software development process|project management|projektmanagement|automation solution"),
]

NIST_PREFIX_MAP = {
    "PW.1": ["HREQ-RISK-004"],
    "PW.2": ["HREQ-RISK-004"],
    "PW.4": ["HREQ-DEV-005"],
    "PW.5": ["HREQ-DEV-002"],
    "PW.6": ["HREQ-SC-001", "HREQ-SC-002"],
    "PW.7": ["HREQ-DEV-003"],
    "PW.8": ["HREQ-TEST-003", "HREQ-TEST-004"],
    "PW.9": ["HREQ-APP-007"],
    "PS.1": ["HREQ-DEV-001"],
    "PS.3": ["HREQ-SC-003"],
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with ZipFile(path) as archive:
        strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.iter(f"{{{XML_NS}}}t"))
            for item in strings_root.findall("m:si", NS)
        ]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    result = []
    for row in sheet.findall(".//m:sheetData/m:row", NS):
        row_number = int(row.attrib["r"])
        if not 4 <= row_number <= 267:
            continue
        values: dict[str, str] = {}
        for cell in row.findall("m:c", NS):
            column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
            value_node = cell.find("m:v", NS)
            value = "" if value_node is None else (value_node.text or "")
            if cell.attrib.get("t") == "s" and value:
                value = shared[int(value)]
            values[column] = value.strip()
        if any(values.get(column) for column in "BCDEFGHIJKL"):
            result.append(values)
    return result


def source_strength(description: str, priority: str) -> str:
    text = f"{description} {priority}"
    if re.search(r"\b(?:MUST|SHALL|MUSS|MÜSSEN|M /|M$)\b", text, re.IGNORECASE):
        return "must"
    if re.search(r"\b(?:SHOULD|SOLLTE|SOLLTEN|R /|R$)\b", text, re.IGNORECASE):
        return "should"
    if re.search(r"\b(?:MAY|KANN)\b", text, re.IGNORECASE):
        return "may"
    return "unclassified"


def classify(standard_id: str, requirement_id: str, text: str) -> tuple[list[str], str, str]:
    exact = EXACT_SOURCE_ID_MAP.get((standard_id, requirement_id))
    if exact:
        return exact, "source_identifier", "high"
    if standard_id == "NIST-SP-800-218":
        for prefix, targets in NIST_PREFIX_MAP.items():
            if requirement_id.startswith(prefix):
                return targets, "source_identifier", "high"

    base_targets = ["HREQ-SC-006"] if standard_id == "BSI-TR-03183-2" else []

    targets = list(base_targets)
    for target, pattern in CONTENT_RULES:
        if re.search(pattern, text, re.IGNORECASE) and target not in targets:
            targets.append(target)
        if len(targets) == 5:
            break
    if targets:
        if base_targets and len(targets) == len(base_targets):
            return targets, "source_identifier", "high"
        return targets, "content_classification", "medium"
    return ["HREQ-GOV-001"], "fallback_classification", "low"


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Harmonized Requirements Candidate Coverage",
        "",
        "This report is non-normative decision support. It does not authorize controls, policy, releases, enforcement, or consumer compliance claims.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Harmonized requirements | {summary['harmonized_requirements']} |",
        f"| Covered | {summary['covered']} |",
        f"| Partial | {summary['partial']} |",
        f"| Gap | {summary['gap']} |",
        f"| Unique source requirements | {summary['source_requirements']} |",
        f"| Source requirements mapped to covered requirements | {summary['source_covered']} |",
        f"| Source requirements mapped to partial requirements | {summary['source_partial']} |",
        f"| Source requirements mapped to gap requirements | {summary['source_gap']} |",
        f"| Weighted preliminary design coverage | {summary['weighted_design_coverage_pct']:.1f}% |",
        "",
        "The weighted value counts covered as 1.0, partial as 0.5, and gap as 0.0. It is not an operational compliance percentage.",
        "",
        "## Harmonized Requirements",
        "",
        "| ID | Area | Coverage | Source mappings | Gap |",
        "|---|---|---|---:|---|",
    ]
    for item in report["coverage_by_requirement"]:
        gap = item["gap"] or "-"
        lines.append(
            f"| `{item['id']}` {item['title']} | `{item['target_area']}` | `{item['status']}` | "
            f"{item['mapped_source_requirements']} | {gap} |"
        )
    lines.extend(
        [
            "",
            "## Decision Boundary",
            "",
            "All mappings require human review. Candidate material must not change runtime governance or released baselines before approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-xlsx", type=Path, required=True)
    parser.add_argument(
        "--requirements-model",
        type=Path,
        default=ROOT / "model" / "requirements" / "harmonized-devsecops-requirements.yaml",
    )
    parser.add_argument(
        "--mapping-output",
        type=Path,
        default=ROOT / "model" / "traceability" / "standards-to-harmonized-requirements.yaml",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=ROOT / "generated" / "reports" / "harmonized-requirements-coverage.json",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=ROOT / "generated" / "reports" / "harmonized-requirements-coverage.md",
    )
    args = parser.parse_args()

    model = yaml.safe_load(args.requirements_model.read_text(encoding="utf-8"))
    requirements = {item["id"]: item for item in model["requirements"]}
    rows = load_rows(args.input_xlsx)
    missing_source_ids = sum(not row.get("C") for row in rows)
    composite = Counter((row.get("B", ""), row.get("C", "")) for row in rows if row.get("C"))
    duplicate_identifier_pairs = sum(count > 1 for count in composite.values())

    standard_counts = Counter(row.get("B", "") for row in rows)
    unknown_standards = sorted(set(standard_counts) - set(STANDARD_ALIASES))
    if unknown_standards:
        raise SystemExit(f"Unclassified source labels: {unknown_standards}")

    by_description: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_description[row.get("G", "")].append(row)

    mappings = []
    fallback_number = 0
    for description, occurrences in sorted(by_description.items(), key=lambda item: hashlib.sha256(item[0].encode()).hexdigest()):
        digest = hashlib.sha256(description.encode("utf-8")).hexdigest().upper()
        source_refs = []
        strengths = set()
        all_targets = []
        bases = []
        confidences = []
        for row in occurrences:
            standard_id, _ = STANDARD_ALIASES[row["B"]]
            requirement_id = row.get("C", "")
            if not requirement_id:
                fallback_number += 1
                requirement_id = f"UNASSIGNED-{fallback_number:03d}"
            ref = {"standard_id": standard_id, "requirement_id": requirement_id}
            if ref not in source_refs:
                source_refs.append(ref)
            strengths.add(source_strength(description, row.get("H", "")))
            searchable = " ".join(row.get(column, "") for column in "DEFG")
            targets, basis, confidence = classify(standard_id, requirement_id, searchable)
            for target in targets:
                if target not in all_targets:
                    all_targets.append(target)
            bases.append(basis)
            confidences.append(confidence)

        unknown_targets = sorted(set(all_targets) - set(requirements))
        if unknown_targets:
            raise SystemExit(f"Mapping references unknown harmonized requirements: {unknown_targets}")
        basis = "source_identifier" if "source_identifier" in bases else (
            "content_classification" if "content_classification" in bases else "fallback_classification"
        )
        confidence = "high" if "high" in confidences else ("medium" if "medium" in confidences else "low")
        mappings.append(
            {
                "id": f"SRCREQ-{digest[:12]}",
                "source_refs": sorted(source_refs, key=lambda item: (item["standard_id"], item["requirement_id"])),
                "occurrence_count": len(occurrences),
                "source_strengths": sorted(strengths),
                "harmonized_requirement_ids": all_targets[:5],
                "mapping_basis": basis,
                "confidence": confidence,
                "review_status": "human_review_required",
            }
        )

    mapping_payload = {
        "schema_version": "0.1.0",
        "mapping_id": "CISO-STANDARDS-TO-HARMONIZED-REQUIREMENTS",
        "status": "candidate",
        "normative": False,
        "source_document_id": "CISO-REQ-SRC-001",
        "source_workbook_digest": f"sha256:{hashlib.sha256(args.input_xlsx.read_bytes()).hexdigest()}",
        "public_source_text_included": False,
        "summary": {
            "raw_rows": len(rows),
            "unique_source_requirements": len(mappings),
            "duplicate_identifier_pairs": duplicate_identifier_pairs,
            "missing_source_ids": missing_source_ids,
            "mapped_source_requirements": len(mappings),
            "unmapped_source_requirements": 0,
        },
        "standards": [
            {
                "standard_id": STANDARD_ALIASES[label][0],
                "source_label": STANDARD_ALIASES[label][1],
                "raw_rows": count,
            }
            for label, count in sorted(standard_counts.items(), key=lambda item: STANDARD_ALIASES[item[0]][0])
        ],
        "mappings": mappings,
    }

    mapped_counts = Counter()
    source_status = Counter()
    rank = {"covered": 0, "partial": 1, "gap": 2}
    for mapping in mappings:
        statuses = []
        for target in mapping["harmonized_requirement_ids"]:
            mapped_counts[target] += 1
            statuses.append(requirements[target]["coverage"]["status"])
        source_status[max(statuses, key=lambda status: rank[status])] += 1

    requirement_status = Counter(item["coverage"]["status"] for item in requirements.values())
    weighted = (source_status["covered"] + 0.5 * source_status["partial"]) / len(mappings) * 100
    report = {
        "schema_version": "0.1.0",
        "report_id": "harmonized-requirements-candidate-coverage",
        "status": "candidate",
        "normative": False,
        "enforcement": "none",
        "source_document_id": "CISO-REQ-SRC-001",
        "summary": {
            "harmonized_requirements": len(requirements),
            "covered": requirement_status["covered"],
            "partial": requirement_status["partial"],
            "gap": requirement_status["gap"],
            "source_requirements": len(mappings),
            "source_covered": source_status["covered"],
            "source_partial": source_status["partial"],
            "source_gap": source_status["gap"],
            "weighted_design_coverage_pct": round(weighted, 1),
        },
        "coverage_by_requirement": [
            {
                "id": item["id"],
                "title": item["title"],
                "domain": item["domain"],
                "target_area": item["target_area"],
                "status": item["coverage"]["status"],
                "refs": item["coverage"]["refs"],
                "gap": item["coverage"]["gap"],
                "mapped_source_requirements": mapped_counts[item["id"]],
            }
            for item in requirements.values()
        ],
        "decision_boundary": {
            "control_changes_authorized": False,
            "policy_changes_authorized": False,
            "release_changes_authorized": False,
            "consumer_compliance_claim_authorized": False,
        },
    }

    for output in (args.mapping_output, args.report_json, args.report_md):
        output.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_output.write_text(yaml.safe_dump(mapping_payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    args.report_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {args.mapping_output.relative_to(ROOT)}")
    print(f"Wrote {args.report_json.relative_to(ROOT)}")
    print(f"Wrote {args.report_md.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
