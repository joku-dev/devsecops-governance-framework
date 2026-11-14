"""Private, read-only requirement impact hints from exact recorded bindings.

These hints describe review needs, not semantic change risk or runtime execution.
They must never be persisted as decisions or copied into a review packet.
"""
import hashlib
from pathlib import Path
import re

import yaml


class ImpactProjection:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.catalog = self.rows('model/requirements/governance-requirement-catalog.yaml', 'requirements')
        self.mappings = self.rows('model/requirements/requirement-to-artifact-register.yaml', 'entries')
        self.cases = []
        for path in sorted((self.root / 'model/requirements/lifecycle-cases').glob('*.json')):
            value = self.read(str(path.relative_to(self.root)))
            if isinstance(value.get('source'), dict) and isinstance(value.get('proposals'), list):
                self.cases.append((value, str(path.relative_to(self.root))))
            else:
                self.errors.append('Lifecycle-Datensatz ist unvollständig.')

    def path(self, value):
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            return None
        target = (self.root / value).resolve()
        return target if target.is_relative_to(self.root) else None

    def read(self, value):
        try:
            path = self.path(value)
            result = yaml.safe_load(path.read_text()) if path else None
            if not isinstance(result, dict):
                raise ValueError('mapping required')
            return result
        except (OSError, ValueError, yaml.YAMLError):
            self.errors.append('Zuordnungsnachweis fehlt oder ist unlesbar: ' + value)
            return {}

    def rows(self, path, key):
        rows = self.read(path).get(key)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            self.errors.append('Zuordnungsnachweis ist unvollständig: ' + path)
            return []
        return rows

    def exists(self, value):
        path = self.path(value)
        return bool(path and path.is_file())

    def hash_matches(self, value, expected):
        path = self.path(value)
        try:
            return bool(path and path.is_file() and isinstance(expected, str)
                        and re.fullmatch(r'[a-f0-9]{64}', expected)
                        and hashlib.sha256(path.read_bytes()).hexdigest() == expected)
        except OSError:
            return False

    @staticmethod
    def statement(value):
        return ' '.join(re.sub(r'^\s*\[[A-Z0-9-]+\]\s*', '', value or '').split())

    def project(self, source, source_hash, requirements, registered):
        try:
            return self._project(source, source_hash, requirements, registered)
        except (TypeError, AttributeError, KeyError, ValueError):
            return {row['id']: {'requirement_ref': None, 'mappings': [], 'risk': 'unknown',
                               'reasons': ['Zuordnungsnachweise sind unvollständig oder ungültig.']}
                    for row in requirements}

    def _project(self, source, source_hash, requirements, registered):
        result = {}
        exact_sources = [s for s in registered if s.get('id') == source.get('id')]
        source_bound = (len(exact_sources) == 1 and exact_sources[0] == source
                        and source.get('status') == 'approved'
                        and self.hash_matches(source.get('source_path'), source_hash))
        for row in requirements:
            reasons = list(self.errors)
            item = {'requirement_ref': None, 'mappings': [], 'risk': 'unknown', 'reasons': reasons,
                    'publication': 'Nicht anforderungsbezogen verknüpft',
                    'runtime': 'Kein anforderungsbezogener Ausführungsnachweis verknüpft'}
            result[row['id']] = item
            if not source_bound:
                reasons.append('Die betrachtete Quelle ist nicht exakt an eine aktuelle freigegebene Registrierung gebunden.')
                continue
            if row.get('identification_class') not in {'explicit_identifier', 'author_identified'}:
                reasons.append('Historischer Eintrag; keine aktuelle explizite Anforderungsdeklaration.')
                continue
            refs = {row.get('extraction_row_id'), row.get('source_requirement_id')} - {None, ''}
            matches = [(case, p, path) for case, path in self.cases
                       for p in case['proposals'] if isinstance(p, dict)
                       and p.get('source_requirement_id') in refs
                       and case['source'].get('source_id') == source['id']]
            if len(matches) != 1:
                reasons.append('Eine eindeutige Lifecycle-Verbindung fehlt; keine Zuordnung aus Textähnlichkeit.')
                continue
            case, proposal, case_path = matches[0]
            binding = case['source']
            decision, activation = proposal.get('decision') or {}, proposal.get('activation') or {}
            if (binding.get('source_path') != source['source_path'] or binding.get('source_sha256') != source_hash
                    or self.statement(proposal.get('statement')) != self.statement(row.get('statement'))
                    or decision.get('disposition') != 'approve' or not activation
                    or not self.exists(decision.get('decision_ref'))):
                reasons.append('Quellenstand, Wortlaut, Freigabe oder Aktivierung ist nicht vollständig belegt.')
                continue
            rid, revision = activation.get('requirement_id'), activation.get('revision')
            records = [r for r in self.catalog if r.get('id') == rid]
            revisions = [v for r in records for v in r.get('revisions', [])
                         if isinstance(v, dict) and v.get('revision') == revision]
            if (len(records) != 1 or len(revisions) != 1 or records[0].get('active_revision') != revision
                    or revisions[0].get('status') != 'effective'):
                reasons.append('Die exakt aktivierte Katalogrevision ist nicht eindeutig, aktiv und wirksam.')
                continue
            canonical = revisions[0]
            source_refs = canonical.get('source_refs', [])
            if (proposal.get('source_requirement_id') not in source_refs
                    or self.statement(canonical.get('statement')) != self.statement(row.get('statement'))
                    or canonical.get('decision_ref') != decision.get('decision_ref')):
                reasons.append('Die Katalogrevision bestätigt Quellfundstelle, Wortlaut oder Entscheidungsbeleg nicht.')
                continue
            ref = f'{rid}@rev{revision}'
            item.update(requirement_ref=ref, lifecycle_path=case_path, decision_ref=canonical.get('decision_ref'))
            for mapping in self.mappings:
                if mapping.get('requirement_ref') != ref:
                    continue
                artifact, adoption = mapping.get('artifact') or {}, mapping.get('decision') or {}
                mapped_refs = mapping.get('source_requirement_refs', [])
                evidence = adoption.get('equivalence_evidence', [])
                valid = (sum(m.get('id') == mapping.get('id') for m in self.mappings) == 1
                         and bool(mapped_refs) and set(mapped_refs).issubset(set(source_refs))
                         and proposal['source_requirement_id'] in mapped_refs
                         and artifact.get('type') in canonical.get('authorized_derivations', [])
                         and adoption.get('status') == 'effective'
                         and adoption.get('equivalence') in {'equivalent', 'partial'}
                         and self.exists(adoption.get('decision_ref')) and bool(evidence)
                         and all(self.exists(e) for e in evidence)
                         and self.hash_matches(artifact.get('path'), artifact.get('sha256')))
                item['mappings'].append({'id': mapping.get('id'), 'path': artifact.get('path'),
                    'artifact_id': artifact.get('artifact_id'), 'type': artifact.get('type'),
                    'confirmed': valid, 'coverage': adoption.get('equivalence'),
                    'decided_at': adoption.get('decided_at'), 'decision_ref': adoption.get('decision_ref'),
                    'sha256': artifact.get('sha256'), 'enforcement_authorization': mapping.get('enforcement'),
                    'reason': 'Bindung, Entscheidung und Dateihash bestätigt' if valid else
                              'Bindung, Entscheidung, Ableitungsrecht, Beleg oder Dateihash ungeklärt'})
            if not item['mappings']:
                reasons.append('Keine bestätigte Artefaktzuordnung für diese Revision vorhanden.')
            elif any(not m['confirmed'] for m in item['mappings']):
                reasons.append('Mindestens eine Zuordnung ist unvollständig oder passt nicht zum aktuellen Artefaktstand.')
            elif not reasons:
                item['risk'] = 'review_required'
                reasons.append('Bestätigte Artefaktzuordnungen sind auf Auswirkungen einer Änderung zu prüfen.')
                if any(m['coverage'] == 'partial' for m in item['mappings']):
                    reasons.append('Die bestätigte Abdeckung ist mindestens einmal nur teilweise.')
            reasons.append('Laufzeitwirkung, Consumer und Baseline-Veröffentlichung sind separat nachzuweisen.')
        return result
