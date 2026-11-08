"""Allowlisted, read-only pilot projection; no extraction or inferred relationships."""
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import quote

import yaml

REGISTER = 'model/documents/source-document-register.yaml'
CATALOG = 'model/requirements/governance-requirement-catalog.yaml'
ARTIFACTS = 'model/requirements/requirement-to-artifact-register.yaml'
CASES = 'model/requirements/lifecycle-cases'
PRA = 'RLC-PRA-STD-REQ-001-MIGRATION'
PILOTS = (
    ('GRQ-000003@rev1', 'Branch Protection · bestätigte OPA-Zuordnung'),
    ('GRQ-000001@rev1', 'Aktive Anforderung · ohne bestätigte Zuordnung'),
    ('GRQ-000048@rev1', 'Mehrere bestätigte Plattformzuordnungen'),
    (PRA + '-P0001', 'Historischer Vorschlag · Entscheidung offen'),
    (PRA + '-P0004', 'Historischer Vorschlag · abgelehnt'),
    (PRA + '-P0008', 'Historischer Vorschlag · bestätigtes Duplikat'),
)
PHASES = ('Quelle freigeben', 'Anforderung entscheiden', 'Umsetzung bestätigen',
          'Regelstand veröffentlichen', 'Anwenden und Ergebnisse prüfen')


def project(root: Path, repository_revision=None) -> dict:
    """Read only the four authority inputs and referenced bytes. Never mutate state.

    The caller supplies the repository revision. Missing/malformed/ambiguous input
    stays visible; private proposal text, analysis and rationale are not exported.
    """
    root = root.resolve()
    revision = repository_revision if re.fullmatch(r'[0-9a-f]{40}', repository_revision or '') else None
    errors = []

    def path_for(path):
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            return None
        target = (root / path).resolve()
        return target if target.is_relative_to(root) else None

    def read(path):
        target = path_for(path)
        try:
            value = yaml.safe_load(target.read_text(encoding='utf-8')) if target else None
            if not isinstance(value, dict):
                raise ValueError('mapping required')
            return value
        except (OSError, ValueError, yaml.YAMLError):
            errors.append(f'Datensatz fehlt oder ist unlesbar: {path}')
            return {}

    def link(path, label):
        if not revision or not path_for(path):
            return []
        return [{'label': label, 'url': 'https://github.com/joku-dev/devsecops-governance-framework/blob/'
                 + revision + '/' + quote(path, safe='/')}]

    def hash_check(path, expected):
        target = path_for(path)
        if target is None or not target.is_file():
            return 'Datei fehlt', None
        actual = sha256(target.read_bytes()).hexdigest()
        if not expected:
            return 'Referenzhash fehlt', actual
        return ('Hash stimmt überein' if actual == expected else 'Hash weicht ab'), actual

    sources = read(REGISTER).get('documents', [])
    catalog = read(CATALOG).get('requirements', [])
    mappings = read(ARTIFACTS).get('entries', [])
    case_dir = root / CASES
    case_rows = []
    for path in sorted(case_dir.glob('*.json')):
        case = read(path.relative_to(root).as_posix())
        for proposal in case.get('proposals', []):
            case_rows.append((case, proposal, path.relative_to(root).as_posix()))
    if not case_rows:
        errors.append('Lifecycle-Aufzeichnungen fehlen.')

    journeys = []
    for pilot_id, title in PILOTS:
        historical = not pilot_id.startswith('GRQ-')
        phases = [{'number': n + 1, 'title': name, 'decision': 'Keine Entscheidung verknüpft',
                   'evidence': 'Nicht verknüpft', 'branches': [], 'links': []}
                  for n, name in enumerate(PHASES)]
        issues = list(errors)
        if not revision:
            issues.append('Repository-Revision fehlt; versionierte Beleglinks sind nicht verfügbar.')
        statement = None
        selected = []
        source_refs = []
        requirement = None
        canonical = None
        if historical:
            selected = [row for row in case_rows if row[0].get('case_id') == PRA
                        and row[1].get('proposal_id') == pilot_id]
            if len(selected) != 1:
                issues.append('Historischer Vorschlag fehlt oder ist mehrdeutig.')
                selected = []
        else:
            requirement, rev = pilot_id.split('@rev')
            matches = [r for r in catalog if r.get('id') == requirement]
            revisions = [v for r in matches for v in r.get('revisions', []) if v.get('revision') == int(rev)]
            if len(matches) != 1 or len(revisions) != 1:
                issues.append('Exakte Katalogrevision fehlt oder ist mehrdeutig; kein Ersatz durch eine neuere Revision.')
            else:
                canonical = revisions[0]
                source_refs = canonical.get('source_refs', [])
                if matches[0].get('active_revision') == int(rev) and canonical.get('status') == 'effective':
                    statement = canonical.get('statement')
                    phases[1]['decision'] = 'Aktive, freigegebene GRQ-Revision'
                else:
                    issues.append('Angeforderte GRQ-Revision ist nicht aktiv und wirksam; Katalogtext wird nicht veröffentlicht.')
                    phases[1]['decision'] = 'Revision nicht aktiv und wirksam'
                phases[1]['links'] = link(CATALOG, 'Exakte Revision im Katalog') + link(canonical.get('decision_ref'), 'Katalogentscheidung')
                for ref in source_refs:
                    rows = [row for row in case_rows if row[1].get('source_requirement_id') == ref]
                    if len(rows) != 1:
                        issues.append(f'Quellfundstelle fehlt oder ist mehrdeutig: {ref}')
                    else:
                        selected.extend(rows)
                if not source_refs:
                    issues.append('Keine Quellfundstellen in der exakten Katalogrevision.')

        decisions = []
        for case, proposal, case_path in selected:
            source = case.get('source', {})
            sid, source_path = source.get('source_id'), source.get('source_path')
            registered = [s for s in sources if s.get('id') == sid]
            valid_source = len(registered) == 1 and registered[0].get('source_path') == source_path
            integrity, actual = hash_check(source_path, source.get('source_sha256'))
            source_status = registered[0].get('status', 'unbekannt') if valid_source else 'Registerbindung fehlt oder ist mehrdeutig'
            if not valid_source or source_status != 'approved' or integrity != 'Hash stimmt überein':
                issues.append(f'Quelle {sid}: {source_status}; {integrity}.')
            phases[0]['branches'].append({'label': sid, 'fields': {
                'Quellenstatus': source_status, 'Version': registered[0].get('version') if valid_source else None,
                'Technische Quellfundstelle': proposal.get('source_requirement_id'),
                'Hashprüfung gegen Lifecycle-Quelle': integrity,
                'Erwarteter SHA-256': source.get('source_sha256'), 'Datei-SHA-256': actual},
                'links': link(REGISTER, 'Quellenregister') + link(source_path, 'Quelldokument') + link(case_path, 'Lifecycle-Aufzeichnung')})
            decision = proposal.get('decision') or {}
            activation = proposal.get('activation') or {}
            duplicate = decision.get('disposition') == 'approve' and decision.get('classification') == 'duplicate'
            rejected = decision.get('disposition') == 'reject'
            decision_label = ('Abgelehnt · dieser Vorschlagspfad endet hier' if rejected else
                              'Bestätigte Duplikatentscheidung · keine eigene Aktivierung' if duplicate else
                              'Angenommen' if decision.get('disposition') == 'approve' else 'Entscheidung offen')
            decisions.append(decision_label)
            fields = {'Proposal': proposal.get('proposal_id'), 'Entscheidung': decision_label,
                      'Klassifikation': decision.get('classification'), 'Entscheidungsrolle': decision.get('decision_role'),
                      'Entschieden am': decision.get('decided_at')}
            if duplicate:
                target = decision.get('target_requirement_id')
                fields['Duplikatziel'] = target
                fields['Zielrevision'] = 'Nicht im Entscheidungsdatensatz festgelegt; keine eigene GRQ-Aktivierung'
                if len([r for r in catalog if r.get('id') == target]) != 1:
                    issues.append('Duplikatziel fehlt im Katalog oder ist mehrdeutig.')
            elif not historical:
                bound = activation.get('requirement_id') == requirement and activation.get('revision') == int(rev)
                consistent = decision.get('disposition') == 'approve' and not rejected
                if not bound or not consistent:
                    issues.append(f'Aktivierung/Entscheidung ist nicht exakt an {pilot_id} gebunden: {proposal.get("proposal_id")}')
                fields['Aktivierungsbindung'] = 'Exakte ID und Revision belegt' if bound and consistent else 'Nicht belegt'
            phases[1]['branches'].append({'label': proposal.get('proposal_id'), 'fields': fields,
                'links': link(case_path, 'Lifecycle-Aufzeichnung') + link(decision.get('decision_ref'), 'Entscheidungsbeleg')})
        if selected:
            phases[0]['decision'] = '; '.join(f"{b['label']}: {b['fields']['Quellenstatus']}" for b in phases[0]['branches'])
            phases[0]['evidence'] = '; '.join(b['fields']['Hashprüfung gegen Lifecycle-Quelle'] for b in phases[0]['branches'])
            phases[1]['evidence'] = 'Gespeicherte Entscheidung und Aktivierungsbindung separat ausgewiesen'
            if historical:
                phases[1]['decision'] = decisions[0]
                phases[1]['evidence'] = ('Kein Entscheidungsbeleg; keine Aktivierung' if not (selected[0][1].get('decision') or {}) else
                                         'Duplikatbeleg; keine eigene Aktivierung vorgesehen' if (selected[0][1].get('decision') or {}).get('classification') == 'duplicate' else
                                         'Ablehnungsbeleg; ohne neue Aktivierung')
        if not historical and canonical:
            exact = [m for m in mappings if m.get('requirement_ref') == pilot_id]
            for mapping in exact:
                artifact, decision = mapping.get('artifact', {}), mapping.get('decision', {})
                integrity, actual = hash_check(artifact.get('path'), artifact.get('sha256'))
                ids = [m for m in mappings if m.get('id') == mapping.get('id')]
                refs = mapping.get('source_requirement_refs', [])
                valid = (len(ids) == 1 and bool(refs) and set(refs).issubset(set(source_refs))
                         and decision.get('status') == 'effective')
                if not valid or integrity != 'Hash stimmt überein':
                    issues.append(f'Zuordnung {mapping.get("id")}: Bindung/Entscheidung prüfen; {integrity}.')
                phases[2]['branches'].append({'label': mapping.get('id'), 'fields': {
                    'Anforderungsrevision': mapping.get('requirement_ref'), 'Artefakt': artifact.get('path'),
                    'Artefaktkennung': artifact.get('artifact_id'), 'Artefakttyp': artifact.get('type'),
                    'Zuordnungsentscheidung': decision.get('status'),
                    'Exakte Zuordnungsbindung': 'Belegt' if valid else 'Nicht belegt',
                    'Hashprüfung': integrity, 'Erwarteter SHA-256': artifact.get('sha256'), 'Datei-SHA-256': actual,
                    'Enforcement': mapping.get('enforcement')},
                    'links': link(ARTIFACTS, 'Artefaktregister') + link(artifact.get('path'), 'Artefakt')
                             + link(decision.get('decision_ref'), 'Zuordnungsentscheidung')})
            phases[2]['decision'] = '; '.join(f"{b['label']}: {b['fields']['Zuordnungsentscheidung']}" for b in phases[2]['branches']) if exact else 'Keine bestätigte Artefaktzuordnung verknüpft'
            phases[2]['evidence'] = '; '.join(f"{b['label']}: Bindung {b['fields']['Exakte Zuordnungsbindung']}; {b['fields']['Hashprüfung']}" for b in phases[2]['branches']) if exact else 'Nicht verknüpft'
        elif historical:
            phases[2]['decision'] = 'Kein eigener GRQ-Umsetzungspfad aus diesem historischen Vorschlag'
        for phase in phases[3:]:
            phase['decision'] = 'Keine anforderungsbezogene Freigabe verknüpft'
        phases[3]['explanation'] = 'Ein Baseline-Paket oder eine vorhandene Datei ersetzt keine ausdrückliche Bindung dieser Anforderung an einen veröffentlichten Regelstand.'
        phases[4]['explanation'] = 'Erfolgreiche CI und Kontrollresultate ersetzen keinen anforderungsbezogenen Laufnachweis oder eine freigegebene Gate-Wirkung.'
        if historical:
            phases[1]['explanation'] = 'Lifecycle-Historie; zählt nicht zur heutigen Extraktion. Eine Ablehnung erklärt die fachliche Aussage nicht allgemein für unanwendbar. Ein Duplikat erzeugt keine eigene Aktivierung.'
        next_step = ('Die ausgewiesenen Daten- und Bindungslücken prüfen.' if issues else
                     ('Offenen historischen Vorschlag fachlich prüfen; keine automatische Übernahme in heutige Extraktion.' if not (selected[0][1].get('decision') or {}) else
                      'Duplikatentscheidung und gespeichertes Ziel nachvollziehen; keine eigene Aktivierung erforderlich.' if (selected[0][1].get('decision') or {}).get('classification') == 'duplicate' else
                      'Ablehnungsbeleg nachvollziehen; dieser Vorschlag hat keinen neuen GRQ-Pfad.') if historical else
                     'Fehlende Artefaktzuordnung fachlich prüfen.' if not phases[2]['branches'] else
                     'Expliziten anforderungsbezogenen Veröffentlichungsnachweis prüfen.')
        journeys.append({'id': pilot_id, 'title': title, 'kind': 'history' if historical else 'canonical',
                         'statement': statement, 'phases': phases, 'issues': issues, 'next_step': next_step})
    return {'version': 1, 'repository_revision': revision, 'cases': journeys,
            'scope': 'Sechs feste Pilotfälle · lesend · keine neue Extraktion oder Freigabe'}
