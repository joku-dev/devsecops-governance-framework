"""Whole original advisory requirement review; explicit source/output ports only."""
from __future__ import annotations
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import PurePosixPath as Path
import json
import re
from lib.requirement_validation_budget import yaml_text
ARCH_SOURCES = {'ARCH-TPL-REQ-001', 'ARCH-EA-REQ-001', 'ARCH-SA-REQ-001', 'ARCH-PA-REQ-001'}

class ImplementedRequirementMigration:

    def __init__(self, root, output_root, inventory_roots):
        self.root = root
        self.cases = root / 'model/requirements/lifecycle-cases'
        self.out_json = output_root / 'generated/reports/implemented-requirement-migration.json'
        self.out_md = output_root / 'generated/reports/implemented-requirement-migration.md'
        self.inventory_roots = inventory_roots

    def load_yaml(self, path: Path) -> dict:
        return yaml_text(path.read_text(encoding='utf-8'))

    def file_hash(self, path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    def normalized(self, value: str) -> str:
        return ' '.join(re.sub('[^a-z0-9 ]+', ' ', value.lower()).split())

    def artifact(self, path: Path, kind: str, artifact_id: str | None, text: str, source_basis: str | None=None) -> dict:
        return {'path': path.relative_to(self.root).as_posix(), 'type': kind, 'artifact_id': artifact_id, 'sha256': self.file_hash(path), 'comparison_text': text, 'source_basis': source_basis}

    def inventory(self) -> list[dict]:
        items: list[dict] = []
        for path in sorted((self.root / 'model/controls').glob('dscb-*.yaml')):
            for row in self.load_yaml(path).get('requirements', []):
                text = ' '.join((str(row.get(key, '')) for key in ('id', 'title', 'control_objective', 'requirement')))
                items.append(self.artifact(path, 'controls', row.get('id'), text, 'DSCB-STD-REQ-001'))
                rule = row.get('policy_as_code', {}).get('rule')
                if rule and (self.root / rule).is_file():
                    items.append(self.artifact(self.root / rule, 'policies', row.get('id'), text, 'DSCB-STD-REQ-001'))
        for path in sorted((self.root / 'model/platform').glob('*.yaml')):
            data = self.load_yaml(path)
            rows = data.get('capabilities', []) or data.get('levels', [])
            for row in rows:
                text = ' '.join((str(value) for value in row.values() if isinstance(value, (str, int))))
                items.append(self.artifact(path, 'platform', row.get('id') or row.get('level'), text, 'PRA-STD-REQ-001'))
        for path in sorted((self.root / 'architecture').glob('*.yaml')):
            data = self.load_yaml(path)
            rows = data.get('requirements', [])
            for row in rows:
                text = ' '.join((str(row.get(key, '')) for key in ('id', 'title', 'requirement', 'description')))
                items.append(self.artifact(path, 'architecture', row.get('id'), text, 'ARCH-SDD-REQ-001'))
        for root, kind, pattern in self.inventory_roots:
            for path in sorted((item for item in root.rglob(pattern) if item.is_file())):
                items.append(self.artifact(path, kind, None, path.stem.replace('-', ' '), None))
        return items

    def candidate_rows(self, proposals: list[dict], artifacts: list[dict]) -> list[dict]:
        rows = []
        for proposal in proposals:
            source_id = proposal['source_id']
            ranked = []
            for item in artifacts:
                basis = item['source_basis']
                if source_id in ARCH_SOURCES and item['type'] == 'architecture':
                    lineage = 'lineage_confirmation_required'
                elif basis == source_id:
                    lineage = 'source_lineage_match'
                else:
                    continue
                score = SequenceMatcher(None, self.normalized(proposal['statement']), self.normalized(item['comparison_text'])).ratio()
                if score < 0.3:
                    continue
                ranked.append({'artifact_path': item['path'], 'artifact_type': item['type'], 'artifact_id': item['artifact_id'], 'artifact_sha256': item['sha256'], 'similarity': round(score, 4), 'lineage_assessment': lineage, 'review_state': 'human_equivalence_confirmation_required'})
            ranked.sort(key=lambda row: (-row['similarity'], row['artifact_type'], row['artifact_path'], row['artifact_id'] or ''))
            rows.append({'case_id': proposal['case_id'], 'proposal_id': proposal['proposal_id'], 'source_id': source_id, 'source_requirement_id': proposal['source_requirement_id'], 'lifecycle_decision_state': 'recorded' if proposal['decision'] else 'open', 'mapping_candidates': ranked[:8]})
        return rows

    def render_markdown(self, report: dict) -> str:
        summary = report['summary']
        lines = ['# Implemented Requirement Migration', '', 'This report is advisory. It inventories active artifacts and proposes mappings; it does not approve a requirement or an artifact adoption.', '', '## Summary', '', f"- Source requirements: {summary['source_requirements']}", f"- Active artifact records: {summary['artifact_records']}", f"- Requirements with candidates: {summary['requirements_with_candidates']}", f"- Requirements without candidates: {summary['requirements_without_candidates']}", f"- Confirmed register entries: {summary['confirmed_register_entries']}", '', '## Source status', '', '| Source | Total | With candidates | Open |', '|---|---:|---:|---:|']
        for source, row in sorted(report['sources'].items()):
            lines.append(f"| `{source}` | {row['total']} | {row['with_candidates']} | {row['open']} |")
        lines += ['', '## Review rule', '', 'Each candidate needs both a lifecycle decision and a separate approved entry in `model/requirements/requirement-to-artifact-register.yaml`. Architecture candidates retain `ARCH-SDD` lineage until an explicit equivalence decision is recorded.', '']
        return '\n'.join(lines)

    def build(self) -> dict:
        proposals = []
        for path in sorted(self.cases.glob('*.json')):
            case = json.loads(path.read_text(encoding='utf-8'))
            for row in case['proposals']:
                proposals.append({**row, 'case_id': case['case_id'], 'source_id': case['source']['source_id']})
        artifacts = self.inventory()
        candidates = self.candidate_rows(proposals, artifacts)
        register = self.load_yaml(self.root / 'model/requirements/requirement-to-artifact-register.yaml')
        sources: dict[str, dict] = {}
        for row in candidates:
            state = sources.setdefault(row['source_id'], {'total': 0, 'with_candidates': 0, 'open': 0})
            state['total'] += 1
            state['with_candidates'] += bool(row['mapping_candidates'])
            state['open'] += row['lifecycle_decision_state'] == 'open'
        type_counts = Counter((row['type'] for row in artifacts))
        return {'schema_version': '1.0.0', 'report_id': 'IMPLEMENTED-REQUIREMENT-MIGRATION', 'status': 'review_required', 'summary': {'source_requirements': len(proposals), 'artifact_records': len(artifacts), 'requirements_with_candidates': sum((bool(row['mapping_candidates']) for row in candidates)), 'requirements_without_candidates': sum((not row['mapping_candidates'] for row in candidates)), 'confirmed_register_entries': len(register['entries']), 'artifact_types': dict(sorted(type_counts.items()))}, 'sources': sources, 'artifact_inventory': [{key: value for key, value in row.items() if key != 'comparison_text'} for row in artifacts], 'requirement_candidates': candidates}

    def main(self) -> int:
        report = self.build()
        self.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.out_md.write_text(self.render_markdown(report), encoding='utf-8')
        print(f'Wrote {self.out_json.relative_to(self.root)} and {self.out_md.relative_to(self.root)}')
        return 0
