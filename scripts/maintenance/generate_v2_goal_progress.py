#!/usr/bin/env python3
"""Generate current Goal coverage from the parity matrix, without claiming acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.functional_parity import require_frozen_scope

MATRIX = 'config/axiom-v2-functional-parity.json'
OBSERVATION = 'config/axiom-v2-goal-progress.json'
REPORT = 'docs/operations/status/axiom-v2-goal-progress.md'
JSON_REPORT = 'generated/reports/axiom-v2-goal-progress.json'
START = '<!-- V2_GOAL_PROGRESS:start -->'
END = '<!-- V2_GOAL_PROGRESS:end -->'
GROUPS = {'areas': ('Funktionsbereiche', 22), 'entrypoints': ('V1-Einstiegspunkte', 135),
          'ci_workflows': ('V1-CI-Definitionen', 37), 'operating_workflows': ('Betriebsabläufe', 16)}
STATES = {'verified': 'Vollständig nachgewiesen', 'in_progress': 'In Arbeit', 'pending': 'Noch offen'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 4 * 1024**2:
        raise ValueError('Goal input exceeds 4 MiB')
    def invalid_constant(value):
        raise ValueError('nonfinite JSON number')
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant), raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def label(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError('invalid progress label')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid progress count')
    return value


def validate_observation(value, matrix):
    if set(value) != {'schema_version', 'goal_id', 'next_work', 'last_validation'} or type(value['schema_version']) is not int or value['schema_version'] != 1 or value['goal_id'] != matrix['goal_id']:
        raise ValueError('invalid progress observation identity')
    focus = value['next_work']
    if focus is not None:
        if set(focus) != {'title', 'entrypoints', 'next_step'}:
            raise ValueError('invalid next-work fields')
        label(focus['title']); label(focus['next_step'])
        paths = {row['v1_path']: row for row in matrix['entrypoints']}
        if not isinstance(focus['entrypoints'], list) or not focus['entrypoints'] or len(set(focus['entrypoints'])) != len(focus['entrypoints']):
            raise ValueError('invalid next-work scope')
        if any(name not in paths or paths[name]['state'] == 'verified' for name in focus['entrypoints']):
            raise ValueError('next work must name unfinished matrix entrypoints')
    proof = value['last_validation']
    fields = {'observed_at', 'source_revision', 'runtime_source_digest', 'unit_tests', 'unit_test_seconds',
              'unit_tests_skipped', 'installed_groups', 'equal_complete_result_groups', 'compared_result_groups',
              'canonical_profile_complete_results_equal', 'full_dcr_equal', 'full_dcr_sha256', 'ci_workflows',
              'evidence_kind', 'independent_human_approval', 'full_functional_parity', 'comparison_note'}
    if set(proof) != fields:
        raise ValueError('invalid validation observation fields')
    label(proof['comparison_note'])
    time = datetime.fromisoformat(proof['observed_at'].replace('Z', '+00:00'))
    if time.utcoffset() is None:
        raise ValueError('validation observation needs a timezone')
    for name, length in [('source_revision', 40), ('runtime_source_digest', 64), ('full_dcr_sha256', 64)]:
        if not isinstance(proof[name], str) or not re.fullmatch('[a-f0-9]{' + str(length) + '}', proof[name]):
            raise ValueError('invalid validation source/digest')
    for key in ('unit_tests', 'unit_tests_skipped', 'equal_complete_result_groups', 'compared_result_groups'):
        integer(proof[key])
    if proof['unit_tests_skipped'] > proof['unit_tests'] or proof['equal_complete_result_groups'] > proof['compared_result_groups']:
        raise ValueError('contradictory validation counts')
    if type(proof['unit_test_seconds']) not in (int, float) or not 0 < proof['unit_test_seconds'] < 86400:
        raise ValueError('invalid test duration')
    if set(proof['installed_groups']) != {'mac', 'linux'}:
        raise ValueError('both installed-host observations are required')
    for count in proof['installed_groups'].values():
        integer(count)
    if proof['compared_result_groups'] > min(proof['installed_groups'].values()):
        raise ValueError('comparison exceeds installed groups')
    for key in ('canonical_profile_complete_results_equal', 'full_dcr_equal'):
        if type(proof[key]) is not bool:
            raise ValueError('invalid comparison observation')
    if proof['evidence_kind'] != 'declared_technical_validation_observation' or proof['independent_human_approval'] is not False or proof['full_functional_parity'] is not False:
        raise ValueError('test observations cannot grant approval or Goal completion')
    workflows = proof['ci_workflows']
    if not isinstance(workflows, list) or not workflows or len(workflows) > 100:
        raise ValueError('invalid observed workflow family count')
    names, ids = set(), set()
    for row in workflows:
        if set(row) != {'name', 'run_id', 'result', 'url'} or row['result'] != 'passed':
            raise ValueError('only explicit passing workflow observations are supported')
        label(row['name']); label(row['run_id'], 200)
        url = urlsplit(row['url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or any(c.isspace() for c in row['url']):
            raise ValueError('invalid public workflow URL')
        if row['name'] in names or row['run_id'] in ids:
            raise ValueError('duplicate workflow observation')
        names.add(row['name']); ids.add(row['run_id'])


def project(matrix, observation, matrix_raw, observation_raw):
    validate_observation(observation, matrix)
    groups = {}
    for name, (title, expected) in GROUPS.items():
        rows = matrix[name]
        identity = 'id' if name in ('areas', 'operating_workflows') else 'v1_path'
        if len(rows) != expected or len({row[identity] for row in rows}) != expected:
            raise ValueError('Goal scope changed or duplicated: ' + name)
        counts = Counter(row['state'] for row in rows)
        if set(counts) - set(STATES):
            raise ValueError('unknown Goal state')
        groups[name] = {'title': title, 'total': expected, **{state: counts[state] for state in STATES},
                        'remaining': expected - counts['verified'],
                        'verified_percent': round(100 * counts['verified'] / expected, 1),
                        'remaining_subjects': [row[identity] for row in rows if row['state'] != 'verified']}
    return {'schema_version': 1, 'goal_id': matrix['goal_id'],
            'matrix_sha256': sha(matrix_raw), 'observation_sha256': sha(observation_raw),
            'state_basis': 'declared_matrix_states', 'completion_gate_evaluated': False,
            'goal_status': 'open' if any(g['remaining'] for g in groups.values()) else 'final_audit_required',
            'remaining_effort_estimate': None, 'scope_exceptions': [], 'groups': groups,
            'next_work': observation['next_work'], 'last_validation': observation['last_validation'],
            'authority_transferred': False, 'independent_human_approval': False}


def cell(value):
    return html.escape(str(value)).replace('|', '&#124;').replace('`', '&#96;')


def table(report):
    lines = ['| Umfang | Vollständig nachgewiesen¹ | In Arbeit | Noch offen | Insgesamt noch abzuschließen |',
             '| --- | ---: | ---: | ---: | ---: |']
    for row in report['groups'].values():
        lines.append(f"| {row['title']} ({row['total']}) | {row['verified']} | {row['in_progress']} | {row['pending']} | {row['remaining']} |")
    return '\n'.join(lines)


def summary(report):
    g = report['groups']['entrypoints']; proof = report['last_validation']
    status = 'offen' if report['goal_status'] == 'open' else 'Abschlussprüfung ausstehend'
    return '\n'.join(['### V2-Goal: aktueller Fortschritt', '',
        f"**Goal {status}.** Von {g['total']} V1-Einstiegspunkten sind **{g['verified']} vollständig nachgewiesen**, **{g['in_progress']} in Arbeit** und **{g['pending']} noch offen**.", '',
        table(report), '',
        '¹ Zustände der verbindlichen Paritätsmatrix; diese Anzeige führt keine Nachweis- oder Abschlussprüfung aus. „In Arbeit“ zählt nicht als erledigt.', '',
        f"**Letzter geprüfter Kandidat:** `{proof['source_revision'][:7]}` · {proof['unit_tests']:,} Tests (davon {proof['unit_tests_skipped']} übersprungen) · Mac {proof['installed_groups']['mac']} / VM {proof['installed_groups']['linux']} Prüfgruppen · {len(proof['ci_workflows'])} grüne CI-Workflow-Familien.", '',
        '**Nächster Baustein:** ' + cell(report['next_work']['title'] if report['next_work'] else 'Abschlussprüfung vorbereiten') + '.', '',
        'Die Einheiten sind unterschiedlich groß. Aus diesen Zahlen lässt sich keine belastbare Restzeit ableiten; grüne Tests ersetzen keinen vollständigen Paritätsnachweis.', '',
        '[Fortschritt, Nachweise und Restarbeiten](docs/operations/status/axiom-v2-goal-progress.md) · automatisch aus der Matrix erzeugt; veraltete Anzeigen werden in CI erkannt.'])


def document(report, matrix):
    proof = report['last_validation']
    readme = summary(report).replace('### V2-Goal: aktueller Fortschritt', '# V2-Goal: aktueller Fortschritt')
    readme = readme.replace('[Fortschritt, Nachweise und Restarbeiten](docs/operations/status/axiom-v2-goal-progress.md) · automatisch aus der Matrix erzeugt; veraltete Anzeigen werden in CI erkannt.',
        'Die Anzeige wird aus der Matrix erzeugt; CI erkennt veraltete Ausgaben.')
    lines = ['<!-- Generated by scripts/maintenance/generate_v2_goal_progress.py; do not edit manually. -->', readme, '',
        '## Was die Zahlen bedeuten', '',
        '- **Vollständig nachgewiesen:** als `verified` in der Zielmatrix geführt. Einzelne Implementierungen oder grüne Prüfläufe reichen dafür nicht aus.',
        '- **In Arbeit:** ein V2-Gegenstück ist zugeordnet oder teilweise umgesetzt; vollständige Übernahme und Nachweise fehlen noch.',
        '- **Noch offen:** der jeweilige Matrixeintrag ist weiterhin `pending`.',
        '- **Insgesamt noch abzuschließen:** alle Einträge ohne vollständigen Nachweis, einschließlich laufender Arbeit.', '',
        'Bereiche, Einstiegspunkte, CI-Definitionen und Betriebsabläufe überschneiden sich. Ihre Restzahlen werden deshalb nicht zu einer Gesamtpunktzahl oder Restzeit addiert. Insbesondere sind zehn grüne Workflow-Familien keine Bestätigung der Parität aller 37 V1-CI-Definitionen.', '',
        '## Nächste Arbeit', '', cell(report['next_work']['next_step'] if report['next_work'] else 'Die separate Abschlussprüfung und ihre Nachweise vorbereiten.'), '',
        *('- `' + cell(name) + '`' for name in (report['next_work']['entrypoints'] if report['next_work'] else [])), '',
        '## Letzter vollständiger technischer Prüfstand', '',
        f"Beobachtet: `{proof['observed_at']}`. Geprüfter Quellcommit: `{proof['source_revision']}`. Diese datierte Beobachtung gilt für diesen Kandidaten und zertifiziert spätere Commits nicht automatisch. Die Anzeige fragt keine externen Dienste ab.", '',
        f"- Unit-Tests: {proof['unit_tests']} in {proof['unit_test_seconds']} Sekunden; {proof['unit_tests_skipped']} plattformabhängig übersprungen.",
        f"- Installierte Prüfgruppen: Mac {proof['installed_groups']['mac']}, Linux-VM {proof['installed_groups']['linux']}.",
        f"- Vollständige Ergebnisgruppen: {proof['equal_complete_result_groups']} von {proof['compared_result_groups']} stimmen zwischen den Rechnern überein.",
        '- ' + cell(proof['comparison_note']),
        '- Kanonisches Profil vollständig gleich: **' + ('ja' if proof['canonical_profile_complete_results_equal'] else 'nein') + '**.',
        f"- Vollständiger DCR-Bericht: Gleichheit **{'ja' if proof['full_dcr_equal'] else 'nein'}**; aufgezeichneter Hash `{proof['full_dcr_sha256']}`.",
        '- Technische Beobachtungen sind deklarierte Nachweise und erteilen keine unabhängige menschliche Freigabe.', '',
        '| CI-Workflow-Familie | Beobachteter Lauf | Ergebnis |', '| --- | --- | --- |']
    for row in proof['ci_workflows']:
        lines.append(f"| {cell(row['name'])} | [{cell(row['run_id'])}]({row['url']}) | bestanden |")
    lines += ['', '## Stand aller Funktionsbereiche', '', '| Bereich | Zustand der Matrix |', '| --- | --- |']
    for row in matrix['areas']:
        lines.append('| ' + cell(row['id'] + ' · ' + row['title']) + ' | ' + STATES[row['state']] + ' |')
    lines += ['', '## Aktualisierung und Abschluss', '',
        'Die aktuelle Matrix liegt in `config/axiom-v2-functional-parity.json`. Der nächste Arbeitsbaustein und der letzte datierte Teststand liegen in `config/axiom-v2-goal-progress.json`. Änderungen an der Matrix werden nicht allein aus Testanzahlen abgeleitet.', '',
        '```bash', 'python3 scripts/maintenance/generate_v2_goal_progress.py', 'python3 scripts/maintenance/generate_v2_goal_progress.py --check',
        'python3 scripts/maintenance/generate_v2_goal_progress.py --show', '```', '',
        'Im vollständigen Entwicklungs-Checkout aktualisiert der erste Befehl README, diese Seite und den maschinenlesbaren Bericht `generated/reports/axiom-v2-goal-progress.json`. `--show` zeigt den aktuellen Matrixstand direkt im Terminal, ohne Dateien zu ändern. `--check` schlägt bei veralteten Anzeigen fehl und läuft in CI.', '',
        'Der formale Goal-Abschluss bleibt die separate Prüfung `axiom-v2 parity --reference V1_CHECKOUT --evidence-directory PARITY_RECEIPTS --require-complete`. Sie prüft die erforderlichen positiven, negativen und installierten Nachweise. Diese Übersicht ersetzt sie nicht.', '',
        f"Matrix-SHA-256: `{report['matrix_sha256']}`. Beobachtungs-SHA-256: `{report['observation_sha256']}`.", '',
        'Siehe [vollständigen Paritätsplan](../planning/axiom-v2-functional-parity.md).', '']
    return '\n'.join(lines)


def outputs(root, report, matrix):
    text = (root / 'README.md').read_text()
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) >= text.index(END):
        raise ValueError('README must contain one ordered Goal progress marker pair')
    before, remainder = text.split(START); _, after = remainder.split(END)
    return {'README.md': before + START + '\n' + summary(report) + '\n' + END + after,
            REPORT: document(report, matrix), JSON_REPORT: json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--show', action='store_true')
    args = parser.parse_args(argv); root = args.root.resolve()
    matrix, matrix_raw = read_json(root / MATRIX)
    schema, _ = read_json(root / 'schemas/axiom-v2-functional-parity.schema.json')
    Draft202012Validator(schema).validate(matrix)
    require_frozen_scope(matrix, root)
    observation, observation_raw = read_json(root / OBSERVATION)
    report = project(matrix, observation, matrix_raw, observation_raw)
    if args.show:
        print(summary(report)); return 0
    rendered = outputs(root, report, matrix)
    stale = [name for name, value in rendered.items() if not (root / name).is_file() or (root / name).read_text() != value]
    if args.check:
        if stale:
            print('Outdated Goal progress: ' + ', '.join(stale), file=sys.stderr)
            return 1
        print('Goal progress is current for the matrix and dated observation.'); return 0
    for name, value in rendered.items():
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Goal output path cannot be a symlink')
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
    print('Updated Goal progress: ' + ', '.join(rendered)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
