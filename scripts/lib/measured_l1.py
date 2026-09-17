"""Central, conservative L1 evidence assessment; never a released compliance result."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, FormatChecker
from lib.measured_security import ROOT, SERVICES, REPOSITORY, check_run, normalize as security_normalize

PROFILE = 'ha-cpswms-l1-measured-v1'
BASELINE = 'l1-baseline-v1.1.3'
STATES = ('measured', 'partial', 'findings', 'gap')
FILES = {
    'source': ('junit.xml', 'tests.execution.json', 'bandit.json', 'bandit.execution.json',
               'ruff.json', 'ruff.execution.json', 'installed-tools.log'),
    'platform': ('commit.json', 'pulls.json', 'protection.json', 'rules.json', 'environments.json', 'run.json'),
    'runtime': ('junit.xml', 'runtime-tests.execution.json', 'deployment.json', 'query-api.log', 'neo4j.log'),
}
IMAGE_FILES = ('subject.json', 'image-metadata.json', 'sbom.cyclonedx.json', 'vulnerabilities.json',
               'build.execution.json', 'sbom.execution.json', 'vulnerabilities.execution.json',
               'archive.execution.json', 'trivy-version.log')
FILES.update({'image-' + s: IMAGE_FILES for s in SERVICES})


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact_binding(artifact, run, name):
    binding = artifact['workflow_run']
    if (artifact['name'] != name or artifact['expired'] or str(binding['id']) != str(run['id'])
            or binding['head_sha'] != run['head_sha'] or binding['head_branch'] != 'main'
            or binding['repository_id'] != run['repository']['id']):
        raise ValueError('Artifact/run binding mismatch: ' + name)


def raw_record(raw, artifact_id, verification):
    return {'sha256': digest(raw), 'bytes': len(raw), 'artifact_id': str(artifact_id), 'verification': verification}


def cases(raw):
    text = raw.decode('utf-8-sig')  # Producer JUnit is UTF-8; reject alternate encodings.
    if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/entity declarations are not test evidence')
    result = []
    for case in ET.fromstring(text).iter('testcase'):
        state = next((s for s in ('error', 'failure', 'skipped') if case.find(s) is not None), 'pass')
        result.append({'class': case.get('classname', ''), 'name': case.get('name', ''), 'status': state})
    if not result:
        raise ValueError('Empty JUnit is not test evidence')
    return result


def evaluate(observed, refs):
    """Versioned assessment rules. No approval is inferred from a declaration or job status."""
    rows = []
    def row(number, title, state, tools, observation, remaining, evidence):
        rows.append({'control_id': f'DSCB-L1-REQ-{number:03}', 'title': title, 'assessment': state,
                     'tools': tools, 'observation': observation, 'remaining': remaining, 'evidence_refs': evidence})
    image_refs = ['image-' + s + '/subject.json' for s in SERVICES]
    sbom_refs = ['image-' + s + '/sbom.cyclonedx.json' for s in SERVICES]
    scan_refs = ['image-' + s + '/vulnerabilities.json' for s in SERVICES]
    tests = observed['tests']; static = observed['static_analysis']; platform = observed['platform']
    tests_ok = all(v['execution_ok'] and v['failed'] == 0 and v['skipped'] == 0 for v in tests.values())
    linked = observed['traceability']['matched'] == observed['traceability']['requirements'] > 0
    row(1, 'Anforderungen, Tests und Berichte', 'partial' if tests_ok and linked else 'gap', ['pytest', 'JUnit'],
        f"{sum(v['passed'] for v in tests.values())} Tests bestanden; {observed['traceability']['matched']} technische Anforderungszuordnungen geprüft.",
        'Freigegebene Systemanforderungen und vollständige Abdeckung aller Komponenten nachweisen.',
        ['source/junit.xml', 'runtime/junit.xml', 'repository/quality/traceability.json'])
    row(2, 'Änderungen und Autoren', 'partial' if platform['author_identified'] else 'gap', ['GitHub API'],
        'Commit und identifizierbarer Autor bestätigt.' if platform['author_identified'] else 'Kein bestätigter Autor für diesen Commit.',
        'Organisatorische VCS-Freigabe und benötigte Review-Nachweise separat belegen; kein unabhängiges Review abgeleitet.',
        ['platform/commit.json', 'platform/pulls.json'])
    row(3, 'Geschützte Branches', 'partial' if platform['protection_http'] == 200 else 'gap', ['GitHub API'],
        f"Branch-Schutz HTTP {platform['protection_http']}; Branch-Regeln HTTP {platform['rules_http']}.",
        'Vollständige Schutz- und Bypass-Regeln lesen und Direktänderungsverbot bewerten. API-Zugriff allein beweist keinen Schutz.',
        ['platform/protection.json', 'platform/rules.json'])
    row(4, 'Sichere Entwicklung', 'gap' if not static['execution_ok'] else 'findings' if static['bandit'] + static['ruff'] else 'partial', ['Bandit', 'Ruff'],
        f"{static['bandit']} Bandit- und {static['ruff']} Ruff-Befunde; erfolgreiche Werkzeugausführung: {static['execution_ok']}.",
        'Security-relevante Befunde fachlich bewerten und Entscheidungen dokumentieren.', ['source/bandit.json', 'source/ruff.json'])
    row(5, 'Abhängigkeiten erfassen', 'partial', ['Trivy', 'CycloneDX'],
        f"{observed['component_count']} Komponentenmeldungen in fünf Image-SBOMs (Mehrfachzählungen möglich).",
        'Inventar umfasst Runtime-Images; Entwicklungs- und Build-Abhängigkeiten vollständig ergänzen.', sbom_refs)
    row(6, 'SBOM je Artefakt', 'measured', ['Trivy', 'CycloneDX'],
        'Fünf nichtleere SBOMs mit den gescannten Image-IDs abgeglichen.',
        'Nachweis gilt für diese CI-Builds; keine Release- oder Deployment-Freigabe.', sbom_refs + image_refs)
    row(7, 'Kontrollierte Builds', 'partial', ['Docker', 'GitHub Actions'],
        'Erfolgreiche Build-Ausführung und festgelegte Basis-Image-Digests für fünf Images erfasst.',
        'Python-Abhängigkeiten sperren und reproduzierbare Wiederholungsbuilds nachweisen.',
        ['image-' + s + '/build.execution.json' for s in SERVICES] + image_refs)
    row(8, 'Build-Ergebnisse identifizieren', 'measured', ['Docker', 'SHA-256'],
        'Fünf Image-IDs mit Commit, Scanner- und Docker-Metadaten abgeglichen.',
        'Archive-Digests sind Producer-Angaben; vollständige Image-Archive zentral nicht erneut gehasht.', image_refs)
    row(9, 'Schwachstellen scannen', 'measured', ['Trivy'],
        'Trivy-JSON und erfolgreiche Scan-Ausführung für alle fünf Image-IDs geprüft.',
        'Scan-Abschluss bewertet weder Ausnutzbarkeit noch Risikoakzeptanz.', scan_refs)
    total = sum(observed['vulnerability_counts'].values())
    row(10, 'Schwachstellen bewerten', 'findings' if total else 'partial', ['Trivy'],
        f"{total} Image-/Paketmeldungen, davon {observed['vulnerability_counts']['CRITICAL']} kritisch und {observed['vulnerability_counts']['HIGH']} hoch.",
        'Befunde auf betroffene Nutzung prüfen, beheben oder autorisierte Entscheidungen einholen; keine automatische Risikofreigabe.', scan_refs)
    row(11, 'Artefakte vor Manipulation schützen', 'partial', ['SHA-256', 'GitHub Artifacts'],
        'Ausgewählte Rohdateien gegen laufgebundene Producer-Manifeste geprüft.',
        'Zugriffsschutz, Aufbewahrung und unabhängige Provenienz fehlen in dieser Bewertung; keine Signatur- oder Komplettarchivprüfung.', image_refs)
    row(12, 'Artefaktidentität', 'measured', ['Docker', 'SHA-256'],
        'Image-IDs und Quell-Commit sind durchgängig zugeordnet.',
        'Identität ist keine Aussage über Freigabe oder Vertrauenswürdigkeit des Producers.', image_refs)
    row(13, 'Deployment autorisieren', 'gap', ['GitHub API'],
        f"Umgebungsabfrage HTTP {platform['environments_http']}; keine autorisierte Deployment-Freigabe im Messvertrag.",
        'Zielumgebung und autorisierte Freigabe für das konkrete Artefakt nachweisen. Merge und grüner Lauf reichen nicht.', ['platform/environments.json'])
    row(14, 'Nur freigegebene Artefakte deployen', 'gap', ['Docker', 'pytest'],
        'Query-API und Neo4j wurden mit den gescannten Image-IDs in kurzlebiger CI getestet.',
        'Deployment in eine genehmigte Zielumgebung und dortige Auswahl freigegebener Artefakte nachweisen.', ['runtime/deployment.json'])
    row(15, 'Maschinenlesbare Nachweise', 'measured', ['JSON', 'JUnit', 'SHA-256'],
        'Ausgewählte Nachweisdateien an Repository, Commit, Lauf und Versuch gebunden und zentral geprüft.',
        'Keine unabhängige Attestation; nicht heruntergeladene Archivbytes bleiben ungeprüft.', sorted(k for k in refs if k.endswith('/manifest.json')))
    row(16, 'Betrieb nachvollziehen', 'partial' if tests['runtime']['execution_ok'] and tests['runtime']['failed'] == 0 else 'gap', ['pytest', 'HTTP', 'Neo4j', 'Docker'],
        f"{tests['runtime']['passed']} Runtime-Tests bestanden; Image-IDs und CI-Logs erfasst.",
        'VM, Betriebsregister und dauerhafte Security-Ereignisaufbewahrung ergänzen; CI ist kein Betriebsnachweis.',
        ['runtime/deployment.json', 'runtime/junit.xml', 'runtime/query-api.log', 'runtime/neo4j.log'])
    return rows


def normalize(run, report_raw, report_artifact, bundles, traceability_raw):
    check_run(run, run['repository']['full_name'], run['id'])
    artifact_binding(report_artifact, run, 'l1-control-coverage')
    report = json.loads(report_raw)
    expected = {'repository': REPOSITORY, 'commit': run['head_sha'], 'run_id': str(run['id']),
                'attempt': str(run['run_attempt']), 'event': 'push'}
    if (any(report['context'].get(k) != v for k, v in expected.items()) or report.get('reference_baseline') != BASELINE
            or report.get('report_type') != 'l1-measured-evidence-coverage' or report.get('evidence_errors') != {}
            or report.get('enforcement') != 'report-only' or report.get('official_compliance_result') is not False
            or report.get('production_approval') is not False):
        raise ValueError('Incompatible coverage context or contract')
    producer_ids = [r['control_id'] for r in report['controls']]
    if sorted(producer_ids) != [f'DSCB-L1-REQ-{n:03}' for n in range(1, 17)]:
        raise ValueError('Incomplete or duplicate producer controls')
    sources = {'report/l1-coverage.json': raw_record(report_raw, report_artifact['id'], 'github_artifact_context'),
               'repository/quality/traceability.json': raw_record(traceability_raw, 'repository', 'git_commit_content')}
    parsed = {}
    for name, required in FILES.items():
        files, artifact = bundles[name]
        artifact_binding(artifact, run, 'l1-' + name)
        manifest = json.loads(files['manifest.json'])
        if any(manifest['context'].get(k) != v for k, v in expected.items()):
            raise ValueError('Manifest context mismatch: ' + name)
        sources[name + '/manifest.json'] = raw_record(files['manifest.json'], artifact['id'], 'github_artifact_context')
        for filename in required:
            raw = files[filename]; record = manifest['files'][filename]
            if digest(raw) != record['sha256'] or len(raw) != record['bytes']:
                raise ValueError('Raw evidence hash/size mismatch: ' + name + '/' + filename)
            sources[name + '/' + filename] = raw_record(raw, artifact['id'], 'manifest_sha256')
        parsed[name] = {n: json.loads(files[n]) for n in required if n.endswith('.json')}
    scans = security_normalize(run, report, {s: bundles['image-' + s] for s in SERVICES})
    images = {}; component_count = 0
    for s in SERVICES:
        data = parsed['image-' + s]; subject = data['subject.json']; sbom = data['sbom.cyclonedx.json']
        component = sbom.get('metadata', {}).get('component', {})
        properties = {p.get('name'): p.get('value') for p in component.get('properties', [])}
        if (sbom.get('bomFormat') != 'CycloneDX' or not sbom.get('components') or component.get('type') != 'container'
                or properties.get('aquasecurity:trivy:ImageID') != subject['image_id']
                or data['image-metadata.json']['Id'] != subject['image_id']
                or not re.fullmatch(r'[a-f0-9]{64}', subject['archive_sha256'])
                or not re.search(r'@sha256:[a-f0-9]{64}$', subject.get('python_base') or subject.get('external_image') or '')
                or any(data[n + '.execution.json']['exit_code'] != 0 for n in ('build', 'sbom', 'vulnerabilities', 'archive'))):
            raise ValueError('SBOM/image/build binding invalid: ' + s)
        component_count += len(sbom['components'])
        images[s] = {'image_id': subject['image_id'], 'archive_sha256_declared': subject['archive_sha256']}
    tests = {}; all_cases = []
    for name, execution in [('source', 'tests'), ('runtime', 'runtime-tests')]:
        found = cases(bundles[name][0]['junit.xml']); all_cases.extend(found)
        totals = Counter(c['status'] for c in found)
        tests[name] = {'passed': totals['pass'], 'failed': totals['failure'] + totals['error'],
                       'skipped': totals['skipped'], 'execution_ok': parsed[name][execution + '.execution.json']['exit_code'] == 0}
    if dict(Counter(c['status'] for c in all_cases)) != report['test_summary']:
        raise ValueError('Producer test counts disagree with raw JUnit')
    trace = json.loads(traceability_raw); linked = []
    for req in trace['requirements']:
        matched = [c for c in all_cases if c['class'].startswith(req['test_class_prefix']) and c['name'].startswith(req.get('test_name_prefix', ''))]
        linked.append({'id': req['id'], 'cases': len(matched), 'passed': bool(matched) and all(c['status'] == 'pass' for c in matched)})
    source = parsed['source']; bandit = source['bandit.json']; ruff = source['ruff.json']
    static = {'bandit': len(bandit['results']), 'ruff': len(ruff), 'execution_ok': not bool(bandit.get('errors')) and all(source[n + '.execution.json']['exit_code'] in (0, 1) for n in ('bandit', 'ruff'))}
    if {k: static[k] for k in ('bandit', 'ruff')} != report['static_analysis']:
        raise ValueError('Producer SAST counts disagree with raw reports')
    platform = parsed['platform']; commit = platform['commit.json']; platform_run = platform['run.json']
    if platform_run['http_status'] == 200 and (str(platform_run['data']['id']) != str(run['id']) or platform_run['data']['head_sha'] != run['head_sha']):
        raise ValueError('Platform run identity mismatch')
    if commit['http_status'] == 200 and commit['data']['sha'] != run['head_sha']:
        raise ValueError('Platform commit identity mismatch')
    deployment = parsed['runtime']['deployment.json']
    if (deployment['commit'] != run['head_sha'] or str(deployment['run_id']) != str(run['id'])
            or len(deployment['containers']) != 2
            or {c['image_id'] for c in deployment['containers']} != {images[s]['image_id'] for s in ('query-api', 'neo4j')}
            or any(c['environment'] != 'ephemeral-ci' for c in deployment['containers'])):
        raise ValueError('Runtime images/context do not match scanned CI images')
    observed = {'tests': tests, 'traceability': {'requirements': len(linked), 'matched': sum(r['passed'] for r in linked), 'links': linked},
        'static_analysis': static, 'component_count': component_count, 'vulnerability_counts': scans['counts'],
        'platform': {'author_identified': commit['http_status'] == 200 and bool((commit['data'].get('author') or {}).get('id')),
                     'protection_http': platform['protection.json']['http_status'], 'rules_http': platform['rules.json']['http_status'],
                     'environments_http': platform['environments.json']['http_status']}, 'images': images}
    rows = evaluate(observed, sources)
    result = {'schema_version': '1.0.0', 'result_type': 'measured-l1-assessment', 'profile': PROFILE,
        'repository_id': REPOSITORY, 'reference_baseline': BASELINE, 'run': scans['run'], 'enforcement': 'report-only',
        'official_compliance_result': False, 'production_approval': False, 'risk_acceptance': False,
        'verification': {'selected_raw_files_verified': True, 'archive_digest_verified': False, 'independent_attestation': False},
        'sources': sources, 'observations': observed, 'controls': rows,
        'summary': {s: sum(r['assessment'] == s for r in rows) for s in STATES}}
    result['evidence_binding'] = binding(result)
    validate_snapshot(result)
    return result


def binding(item):
    return digest(json.dumps({'profile': item['profile'], 'run': item['run'], 'sources': item['sources']}, sort_keys=True, separators=(',', ':')).encode())


def validate_snapshot(item):
    schema = json.loads((ROOT / 'schemas/measured-l1-assessment.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item['evidence_binding'] != binding(item):
        raise ValueError('Evidence binding changed')
    if item['controls'] != evaluate(item['observations'], item['sources']):
        raise ValueError('Assessment differs from measured observations')
    if item['summary'] != {s: sum(r['assessment'] == s for r in item['controls']) for s in STATES}:
        raise ValueError('Assessment summary mismatch')
    required_refs = {'report/l1-coverage.json', 'repository/quality/traceability.json'}
    required_refs.update(n + '/' + f for n, fs in FILES.items() for f in ('manifest.json', *fs))
    if set(item['sources']) != required_refs:
        raise ValueError('Incomplete or unexpected verified sources')
    for row in item['controls']:
        if not set(row['evidence_refs']) <= set(item['sources']):
            raise ValueError('Unresolved control evidence')


def store_snapshot(root, item):
    validate_snapshot(item)
    path = root / item['repository_id'].replace('/', '__') / f"run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(item, indent=2, ensure_ascii=False, sort_keys=True) + '\n')
    except FileExistsError:
        if json.loads(path.read_text()) != item:
            raise ValueError('Conflicting assessment; historical snapshot preserved')
    return path


def load_snapshots(root):
    items = []
    for path in sorted(root.rglob('*.json')) if root.exists() else []:
        item = json.loads(path.read_text()); validate_snapshot(item)
        expected = item['repository_id'].replace('/', '__') + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
        if path.is_symlink() or path.relative_to(root).as_posix() != expected:
            raise ValueError('Snapshot path/identity mismatch')
        items.append(item)
    return sorted(items, key=lambda i: (datetime.fromisoformat(i['run']['created_at'].replace('Z', '+00:00')), int(i['run']['id']), i['run']['attempt']))
