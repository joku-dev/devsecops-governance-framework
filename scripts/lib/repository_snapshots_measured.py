"""Original snapshot-validation decisions over explicit retained repository data.

Frozen technical reference: V1 6b557f. No provider calls, snapshot publication,
Trust elevation or operating acceptance are performed by these validators.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from jsonschema import Draft202012Validator, FormatChecker
SERVICES = ('ha-sync', 'query-api', 'semantic-enrichment', 'world-model-chat', 'neo4j')
PROFILE = 'ha-cpswms-l1-measured-v2'
LEGACY_PROFILE = 'ha-cpswms-l1-measured-v1'
BASELINE = 'l1-baseline-v1.1.3'
MAX_JUNIT_BYTES = 32 * 1024 * 1024
STATES = ('measured', 'partial', 'findings', 'gap')
LEGACY_FILES = {'source': ('junit.xml', 'tests.execution.json', 'bandit.json', 'bandit.execution.json', 'ruff.json', 'ruff.execution.json', 'installed-tools.log'), 'platform': ('commit.json', 'pulls.json', 'protection.json', 'rules.json', 'environments.json', 'run.json'), 'runtime': ('junit.xml', 'runtime-tests.execution.json', 'deployment.json', 'query-api.log', 'neo4j.log')}
IMAGE_FILES = ('subject.json', 'image-metadata.json', 'sbom.cyclonedx.json', 'vulnerabilities.json', 'build.execution.json', 'sbom.execution.json', 'vulnerabilities.execution.json', 'archive.execution.json', 'trivy-version.log')
LEGACY_FILES.update({'image-' + s: IMAGE_FILES for s in SERVICES})
DEPENDENCY_PROFILES = ('ha-sync', 'query-api', 'semantic-enrichment', 'world-model-chat', 'application', 'ci')
DEPENDENCY_FILES = ('dependency-locks.json', 'dependency-sbom-application.cyclonedx.json', 'dependency-sbom-application.execution.json', 'dependency-sbom-ci.cyclonedx.json', 'dependency-sbom-ci.execution.json', 'dependency-audit.json', 'dependency-audit.execution.json', *(f'dependency-files/{name}.{suffix}' for name in DEPENDENCY_PROFILES for suffix in ('in', 'lock')))
FILES = {name: tuple(value) for name, value in LEGACY_FILES.items()}
FILES['source'] += DEPENDENCY_FILES
FILES['platform'] += ('rulesets.json', 'ruleset-details.json')
REQUIRED_CHECKS = {'validate-ubuntu', 'validate-debian', 'DevSecOps Governance', 'Architecture Runtime Governance', 'L1 coverage report'}

class MeasuredSnapshots:

    def __init__(self, root, *, validator_class, peers=None):
        self.root = root
        self.validator_class = validator_class
        self.peers = peers

    def digest(self, raw):
        return hashlib.sha256(raw).hexdigest()

    def evaluate(self, observed, refs):
        """Versioned assessment rules. No approval is inferred from a declaration or job status."""
        rows = []

        def row(number, title, state, tools, observation, remaining, evidence):
            rows.append({'control_id': f'DSCB-L1-REQ-{number:03}', 'title': title, 'assessment': state, 'tools': tools, 'observation': observation, 'remaining': remaining, 'evidence_refs': evidence})
        image_refs = ['image-' + s + '/subject.json' for s in SERVICES]
        sbom_refs = ['image-' + s + '/sbom.cyclonedx.json' for s in SERVICES]
        scan_refs = ['image-' + s + '/vulnerabilities.json' for s in SERVICES]
        tests = observed['tests']
        static = observed['static_analysis']
        platform = observed['platform']
        dependencies = observed.get('dependency_inventory')
        tests_ok = all((v['execution_ok'] and v['failed'] == 0 and (v['skipped'] == 0) for v in tests.values()))
        linked = observed['traceability']['matched'] == observed['traceability']['requirements'] > 0
        row(1, 'Anforderungen, Tests und Berichte', 'partial' if tests_ok and linked else 'gap', ['pytest', 'JUnit'], f"{sum((v['passed'] for v in tests.values()))} Tests bestanden; {observed['traceability']['matched']} technische Anforderungszuordnungen geprüft.", 'Freigegebene Systemanforderungen und vollständige Abdeckung aller Komponenten nachweisen.', ['source/junit.xml', 'runtime/junit.xml', 'repository/quality/traceability.json'])
        row(2, 'Änderungen und Autoren', 'partial' if platform['author_identified'] else 'gap', ['GitHub API'], 'Commit und identifizierbarer Autor bestätigt.' if platform['author_identified'] else 'Kein bestätigter Autor für diesen Commit.', 'Organisatorische VCS-Freigabe und benötigte Review-Nachweise separat belegen; kein unabhängiges Review abgeleitet.', ['platform/commit.json', 'platform/pulls.json'])
        if dependencies:
            rule = platform.get('main_ruleset')
            row(3, 'Geschützte Branches', 'measured' if rule else 'partial' if platform['protection_http'] == 200 else 'gap', ['GitHub API'], f"Aktiver Main-Ruleset {rule['id']} ohne Bypass erzwingt Pull Requests und fünf Governance-/Validierungschecks." if rule else f"Branch-Schutz HTTP {platform['protection_http']}; kein vollständiger Main-Ruleset ohne Bypass bestätigt.", 'Die technische Regel ist gemessen; organisatorische Review-Unabhängigkeit bleibt eine getrennte Entscheidung.' if rule else 'Vollständigen Main-Ruleset ohne Bypass für Direktänderungen, Löschung und Force-Push einrichten.', ['platform/protection.json', 'platform/rules.json', 'platform/rulesets.json', 'platform/ruleset-details.json'])
        else:
            row(3, 'Geschützte Branches', 'partial' if platform['protection_http'] == 200 else 'gap', ['GitHub API'], f"Branch-Schutz HTTP {platform['protection_http']}; Branch-Regeln HTTP {platform['rules_http']}.", 'Vollständige Schutz- und Bypass-Regeln lesen und Direktänderungsverbot bewerten. API-Zugriff allein beweist keinen Schutz.', ['platform/protection.json', 'platform/rules.json'])
        row(4, 'Sichere Entwicklung', 'gap' if not static['execution_ok'] else 'findings' if static['bandit'] + static['ruff'] else 'measured' if dependencies else 'partial', ['Bandit', 'Ruff'], f"{static['bandit']} Bandit- und {static['ruff']} Ruff-Befunde; erfolgreiche Werkzeugausführung: {static['execution_ok']}.", 'Keine maschinellen Befunde im geprüften Umfang; fachliche Secure-Design-Prüfung bleibt im Entwicklungsprozess.' if dependencies and static['execution_ok'] and (not static['bandit'] + static['ruff']) else 'Security-relevante Befunde fachlich bewerten und Entscheidungen dokumentieren.', ['source/bandit.json', 'source/ruff.json'])
        if dependencies:
            row(5, 'Abhängigkeiten erfassen', 'measured', ['Trivy', 'CycloneDX', 'pip-audit'], f"{observed['component_count']} Image-Komponentenmeldungen sowie {dependencies['profiles']['application']['package_count']} Anwendungs- und {dependencies['profiles']['ci']['package_count']} CI-/Tool-Pakete geprüft.", 'Inventar ist an diesen Commit und Python 3.12 gebunden; Änderungen erfordern neue Locks und Nachweise.', sbom_refs + ['source/dependency-locks.json', 'source/dependency-sbom-application.cyclonedx.json', 'source/dependency-sbom-ci.cyclonedx.json'])
        else:
            row(5, 'Abhängigkeiten erfassen', 'partial', ['Trivy', 'CycloneDX'], f"{observed['component_count']} Komponentenmeldungen in fünf Image-SBOMs (Mehrfachzählungen möglich).", 'Inventar umfasst Runtime-Images; Entwicklungs- und Build-Abhängigkeiten vollständig ergänzen.', sbom_refs)
        row(6, 'SBOM je Artefakt', 'measured', ['Trivy', 'CycloneDX'], 'Fünf nichtleere SBOMs mit den gescannten Image-IDs abgeglichen.', 'Nachweis gilt für diese CI-Builds; keine Release- oder Deployment-Freigabe.', sbom_refs + image_refs)
        row(7, 'Kontrollierte Builds', 'measured' if dependencies else 'partial', ['Docker', 'GitHub Actions'], 'Erfolgreiche Builds verwenden Digest-festgelegte Basisimages und Python-3.12-Locks mit exakten Versionen und SHA-256-Hashes.' if dependencies else 'Erfolgreiche Build-Ausführung und festgelegte Basis-Image-Digests für fünf Images erfasst.', 'Nachweis gilt für diese automatisierten Builds; byte-identische Container-Reproduktion und unabhängige Provenienz bleiben weiterführend.' if dependencies else 'Python-Abhängigkeiten sperren und reproduzierbare Wiederholungsbuilds nachweisen.', ['image-' + s + '/build.execution.json' for s in SERVICES] + image_refs + (['source/dependency-locks.json'] if dependencies else []))
        row(8, 'Build-Ergebnisse identifizieren', 'measured', ['Docker', 'SHA-256'], 'Fünf Image-IDs mit Commit, Scanner- und Docker-Metadaten abgeglichen.', 'Archive-Digests sind Producer-Angaben; vollständige Image-Archive zentral nicht erneut gehasht.', image_refs)
        row(9, 'Schwachstellen scannen', 'measured', ['Trivy'], 'Trivy-JSON und erfolgreiche Scan-Ausführung für alle fünf Image-IDs geprüft.', 'Scan-Abschluss bewertet weder Ausnutzbarkeit noch Risikoakzeptanz.', scan_refs)
        image_total = sum(observed['vulnerability_counts'].values())
        dependency_total = dependencies['vulnerability_count'] if dependencies else 0
        total = image_total + dependency_total
        row(10, 'Schwachstellen bewerten', 'findings' if total else 'measured' if dependencies else 'partial', ['Trivy', 'pip-audit'] if dependencies else ['Trivy'], f"{image_total} Image-/Paketmeldungen und {dependency_total} Anwendungsabhängigkeitsmeldungen; davon {observed['vulnerability_counts']['CRITICAL']} kritisch und {observed['vulnerability_counts']['HIGH']} hoch." if dependencies else f"{image_total} Image-/Paketmeldungen, davon {observed['vulnerability_counts']['CRITICAL']} kritisch und {observed['vulnerability_counts']['HIGH']} hoch.", 'Befunde auf betroffene Nutzung prüfen, beheben oder autorisierte Entscheidungen einholen; keine automatische Risikofreigabe.', scan_refs + (['source/dependency-audit.json'] if dependencies else []))
        row(11, 'Artefakte vor Manipulation schützen', 'partial', ['SHA-256', 'GitHub Artifacts'], 'Ausgewählte Rohdateien gegen laufgebundene Producer-Manifeste geprüft.', 'Zugriffsschutz, Aufbewahrung und unabhängige Provenienz fehlen in dieser Bewertung; keine Signatur- oder Komplettarchivprüfung.', image_refs)
        row(12, 'Artefaktidentität', 'measured', ['Docker', 'SHA-256'], 'Image-IDs und Quell-Commit sind durchgängig zugeordnet.', 'Identität ist keine Aussage über Freigabe oder Vertrauenswürdigkeit des Producers.', image_refs)
        row(13, 'Deployment autorisieren', 'gap', ['GitHub API'], f"Umgebungsabfrage HTTP {platform['environments_http']}; keine autorisierte Deployment-Freigabe im Messvertrag.", 'Zielumgebung und autorisierte Freigabe für das konkrete Artefakt nachweisen. Merge und grüner Lauf reichen nicht.', ['platform/environments.json'])
        row(14, 'Nur freigegebene Artefakte deployen', 'gap', ['Docker', 'pytest'], 'Query-API und Neo4j wurden mit den gescannten Image-IDs in kurzlebiger CI getestet.', 'Deployment in eine genehmigte Zielumgebung und dortige Auswahl freigegebener Artefakte nachweisen.', ['runtime/deployment.json'])
        row(15, 'Maschinenlesbare Nachweise', 'measured', ['JSON', 'JUnit', 'SHA-256'], 'Ausgewählte Nachweisdateien an Repository, Commit, Lauf und Versuch gebunden und zentral geprüft.', 'Keine unabhängige Attestation; nicht heruntergeladene Archivbytes bleiben ungeprüft.', sorted((k for k in refs if k.endswith('/manifest.json'))))
        row(16, 'Betrieb nachvollziehen', 'partial' if tests['runtime']['execution_ok'] and tests['runtime']['failed'] == 0 else 'gap', ['pytest', 'HTTP', 'Neo4j', 'Docker'], f"{tests['runtime']['passed']} Runtime-Tests bestanden; Image-IDs und CI-Logs erfasst.", 'VM, Betriebsregister und dauerhafte Security-Ereignisaufbewahrung ergänzen; CI ist kein Betriebsnachweis.', ['runtime/deployment.json', 'runtime/junit.xml', 'runtime/query-api.log', 'runtime/neo4j.log'])
        return rows

    def binding(self, item):
        return self.digest(json.dumps({'profile': item['profile'], 'run': item['run'], 'sources': item['sources']}, sort_keys=True, separators=(',', ':')).encode())

    def validate_snapshot(self, item):
        schema = json.loads((self.root / 'schemas/measured-l1-assessment.schema.json').read_text())
        self.validator_class(schema, format_checker=FormatChecker()).validate(item)
        if item['evidence_binding'] != self.binding(item):
            raise ValueError('Evidence binding changed')
        if item['controls'] != self.evaluate(item['observations'], item['sources']):
            raise ValueError('Assessment differs from measured observations')
        if item['summary'] != {s: sum((r['assessment'] == s for r in item['controls'])) for s in STATES}:
            raise ValueError('Assessment summary mismatch')
        profile = item['profile']
        files = FILES if profile == PROFILE else LEGACY_FILES
        if profile == PROFILE and ('dependency_inventory' not in item['observations'] or 'main_ruleset' not in item['observations']['platform']):
            raise ValueError('Current measured profile lacks dependency or ruleset observations')
        required_refs = {'report/l1-coverage.json', 'repository/quality/traceability.json'}
        required_refs.update((n + '/' + f for n, fs in files.items() for f in ('manifest.json', *fs)))
        if set(item['sources']) != required_refs:
            raise ValueError('Incomplete or unexpected verified sources')
        for row in item['controls']:
            if not set(row['evidence_refs']) <= set(item['sources']):
                raise ValueError('Unresolved control evidence')

    def load_snapshots(self, root):
        items = []
        for path in sorted(root.rglob('*.json')) if root.exists() else []:
            item = json.loads(path.read_text())
            self.validate_snapshot(item)
            expected = item['repository_id'].replace('/', '__') + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
            if path.is_symlink() or path.relative_to(root).as_posix() != expected:
                raise ValueError('Snapshot path/identity mismatch')
            items.append(item)
        return sorted(items, key=lambda i: (datetime.fromisoformat(i['run']['created_at'].replace('Z', '+00:00')), int(i['run']['id']), i['run']['attempt']))
