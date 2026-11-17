"""Shared full sixteen-control measured-evidence decisions.

Source lineage: frozen V1 6b557fefe295b58272d2271326576ca3a3687197 /
scripts/lib/measured_l1.py:evaluate. Native wire parsing, facts, identity and
provenance labels are supplied by explicit adapters; no provider is selected here.
"""
import json


def decode_json(raw):
    if not isinstance(raw, (bytes, str)) or len(raw) > 32 * 1024**2:
        raise ValueError('invalid_measured_wire_json')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_measured_json_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def evaluate(observed, refs, *, services, labels):
    """Versioned assessment rules. No approval is inferred from a declaration or job status."""
    rows = []
    def row(number, title, state, tools, observation, remaining, evidence):
        rows.append({'control_id': f'DSCB-L1-REQ-{number:03}', 'title': title, 'assessment': state,
                     'tools': tools, 'observation': observation, 'remaining': remaining, 'evidence_refs': evidence})
    image_refs = ['image-' + s + '/subject.json' for s in services]
    sbom_refs = ['image-' + s + '/sbom.cyclonedx.json' for s in services]
    scan_refs = ['image-' + s + '/vulnerabilities.json' for s in services]
    tests = observed['tests']; static = observed['static_analysis']; platform = observed['platform']
    dependencies = observed.get('dependency_inventory')
    tests_ok = all(v['execution_ok'] and v['failed'] == 0 and v['skipped'] == 0 for v in tests.values())
    linked = observed['traceability']['matched'] == observed['traceability']['requirements'] > 0
    row(1, 'Anforderungen, Tests und Berichte', 'partial' if tests_ok and linked else 'gap', ['pytest', 'JUnit'],
        f"{sum(v['passed'] for v in tests.values())} Tests bestanden; {observed['traceability']['matched']} technische Anforderungszuordnungen geprüft.",
        'Freigegebene Systemanforderungen und vollständige Abdeckung aller Komponenten nachweisen.',
        ['source/junit.xml', 'runtime/junit.xml', 'repository/quality/traceability.json'])
    row(2, 'Änderungen und Autoren', 'partial' if platform['author_identified'] else 'gap', [labels['scm_api']],
        'Commit und identifizierbarer Autor bestätigt.' if platform['author_identified'] else 'Kein bestätigter Autor für diesen Commit.',
        'Organisatorische VCS-Freigabe und benötigte Review-Nachweise separat belegen; kein unabhängiges Review abgeleitet.',
        ['platform/commit.json', 'platform/pulls.json'])
    if dependencies:
        rule = platform.get('main_ruleset')
        row(3, 'Geschützte Branches', 'measured' if rule else 'partial' if platform['protection_http'] == 200 else 'gap', [labels['scm_api']],
            (f"Aktiver Main-Ruleset {rule['id']} ohne Bypass erzwingt Pull Requests und fünf Governance-/Validierungschecks."
             if rule else f"Branch-Schutz HTTP {platform['protection_http']}; kein vollständiger Main-Ruleset ohne Bypass bestätigt."),
            'Die technische Regel ist gemessen; organisatorische Review-Unabhängigkeit bleibt eine getrennte Entscheidung.' if rule
            else 'Vollständigen Main-Ruleset ohne Bypass für Direktänderungen, Löschung und Force-Push einrichten.',
            ['platform/protection.json', 'platform/rules.json', 'platform/rulesets.json', 'platform/ruleset-details.json'])
    else:
        row(3, 'Geschützte Branches', 'partial' if platform['protection_http'] == 200 else 'gap', [labels['scm_api']],
            f"Branch-Schutz HTTP {platform['protection_http']}; Branch-Regeln HTTP {platform['rules_http']}.",
            'Vollständige Schutz- und Bypass-Regeln lesen und Direktänderungsverbot bewerten. API-Zugriff allein beweist keinen Schutz.',
            ['platform/protection.json', 'platform/rules.json'])
    row(4, 'Sichere Entwicklung', 'gap' if not static['execution_ok'] else 'findings' if static['bandit'] + static['ruff'] else 'measured' if dependencies else 'partial', ['Bandit', 'Ruff'],
        f"{static['bandit']} Bandit- und {static['ruff']} Ruff-Befunde; erfolgreiche Werkzeugausführung: {static['execution_ok']}.",
        'Keine maschinellen Befunde im geprüften Umfang; fachliche Secure-Design-Prüfung bleibt im Entwicklungsprozess.'
        if dependencies and static['execution_ok'] and not static['bandit'] + static['ruff']
        else 'Security-relevante Befunde fachlich bewerten und Entscheidungen dokumentieren.', ['source/bandit.json', 'source/ruff.json'])
    if dependencies:
        row(5, 'Abhängigkeiten erfassen', 'measured', ['Trivy', 'CycloneDX', 'pip-audit'],
            f"{observed['component_count']} Image-Komponentenmeldungen sowie {dependencies['profiles']['application']['package_count']} Anwendungs- und {dependencies['profiles']['ci']['package_count']} CI-/Tool-Pakete geprüft.",
            'Inventar ist an diesen Commit und Python 3.12 gebunden; Änderungen erfordern neue Locks und Nachweise.',
            sbom_refs + ['source/dependency-locks.json', 'source/dependency-sbom-application.cyclonedx.json',
                         'source/dependency-sbom-ci.cyclonedx.json'])
    else:
        row(5, 'Abhängigkeiten erfassen', 'partial', ['Trivy', 'CycloneDX'],
            f"{observed['component_count']} Komponentenmeldungen in fünf Image-SBOMs (Mehrfachzählungen möglich).",
            'Inventar umfasst Runtime-Images; Entwicklungs- und Build-Abhängigkeiten vollständig ergänzen.', sbom_refs)
    row(6, 'SBOM je Artefakt', 'measured', ['Trivy', 'CycloneDX'],
        'Fünf nichtleere SBOMs mit den gescannten Image-IDs abgeglichen.',
        'Nachweis gilt für diese CI-Builds; keine Release- oder Deployment-Freigabe.', sbom_refs + image_refs)
    row(7, 'Kontrollierte Builds', 'measured' if dependencies else 'partial', ['Docker', labels['ci']],
        ('Erfolgreiche Builds verwenden Digest-festgelegte Basisimages und Python-3.12-Locks mit exakten Versionen und SHA-256-Hashes.'
         if dependencies else 'Erfolgreiche Build-Ausführung und festgelegte Basis-Image-Digests für fünf Images erfasst.'),
        ('Nachweis gilt für diese automatisierten Builds; byte-identische Container-Reproduktion und unabhängige Provenienz bleiben weiterführend.'
         if dependencies else 'Python-Abhängigkeiten sperren und reproduzierbare Wiederholungsbuilds nachweisen.'),
        ['image-' + s + '/build.execution.json' for s in services] + image_refs
        + (['source/dependency-locks.json'] if dependencies else []))
    row(8, 'Build-Ergebnisse identifizieren', 'measured', ['Docker', 'SHA-256'],
        'Fünf Image-IDs mit Commit, Scanner- und Docker-Metadaten abgeglichen.',
        'Archive-Digests sind Producer-Angaben; vollständige Image-Archive zentral nicht erneut gehasht.', image_refs)
    row(9, 'Schwachstellen scannen', 'measured', ['Trivy'],
        'Trivy-JSON und erfolgreiche Scan-Ausführung für alle fünf Image-IDs geprüft.',
        'Scan-Abschluss bewertet weder Ausnutzbarkeit noch Risikoakzeptanz.', scan_refs)
    image_total = sum(observed['vulnerability_counts'].values())
    dependency_total = dependencies['vulnerability_count'] if dependencies else 0
    total = image_total + dependency_total
    row(10, 'Schwachstellen bewerten', 'findings' if total else 'measured' if dependencies else 'partial',
        ['Trivy', 'pip-audit'] if dependencies else ['Trivy'],
        (f"{image_total} Image-/Paketmeldungen und {dependency_total} Anwendungsabhängigkeitsmeldungen; davon {observed['vulnerability_counts']['CRITICAL']} kritisch und {observed['vulnerability_counts']['HIGH']} hoch."
         if dependencies else f"{image_total} Image-/Paketmeldungen, davon {observed['vulnerability_counts']['CRITICAL']} kritisch und {observed['vulnerability_counts']['HIGH']} hoch."),
        'Befunde auf betroffene Nutzung prüfen, beheben oder autorisierte Entscheidungen einholen; keine automatische Risikofreigabe.',
        scan_refs + (['source/dependency-audit.json'] if dependencies else []))
    row(11, 'Artefakte vor Manipulation schützen', 'partial', ['SHA-256', labels['artifacts']],
        'Ausgewählte Rohdateien gegen laufgebundene Producer-Manifeste geprüft.',
        'Zugriffsschutz, Aufbewahrung und unabhängige Provenienz fehlen in dieser Bewertung; keine Signatur- oder Komplettarchivprüfung.', image_refs)
    row(12, 'Artefaktidentität', 'measured', ['Docker', 'SHA-256'],
        'Image-IDs und Quell-Commit sind durchgängig zugeordnet.',
        'Identität ist keine Aussage über Freigabe oder Vertrauenswürdigkeit des Producers.', image_refs)
    row(13, 'Deployment autorisieren', 'gap', [labels['scm_api']],
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
