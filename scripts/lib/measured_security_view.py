"""HTML projection of measured container findings; no governance result promotion."""
from collections import defaultdict
from html import escape
import re

from lib.measured_security import SERVICES, validate_snapshot


def assessment(package):
    if package == 'linux-libc-dev':
        return 'Headerpaket; VM-Kernel und Module separat prüfen.'
    if package in ('bsdutils', 'libblkid1', 'liblastlog2-2', 'libmount1', 'libsmartcols1', 'libuuid1', 'login', 'mount', 'util-linux'):
        return 'Lokale Mount-/Namespace-Rechte und SUID-Konfiguration prüfen.'
    if package in ('libsystemd0', 'libudev1'):
        return 'Betroffene systemd-Funktion und laufende Prozesse prüfen.'
    if package == 'perl-base':
        return 'Betroffenes Perl-Modul und Verarbeitung fremder Eingaben prüfen.'
    if package in ('libncursesw6', 'libtinfo6', 'ncurses-base', 'ncurses-bin'):
        return 'CLI-Nutzung und fremde Terminaldaten prüfen.'
    if package == 'libacl1':
        return 'Privilegierte ACL-Zugriffe auf beeinflussbare Dateipfade prüfen.'
    if package == 'wget':
        return 'Downloads, Startskripte und Plugin-Verarbeitung prüfen.'
    return 'Angriffspfad und Paketkorrektur prüfen.'


def render(items):
    if not items:
        return '<section id="measured-security" class="viewer-section"><h2>Container Security</h2><p>Keine erfassten Scan-Ergebnisse. Das bedeutet nicht: keine Schwachstellen.</p></section>'
    for item in items:
        validate_snapshot(item)
    # The loader sorts immutable, successful main snapshots by source-run time.
    current = items[-1]
    previous = next((i for i in reversed(items[:-1]) if i['run']['id'] != current['run']['id']), None)
    repo = current['repository_id']
    base = 'https://github.com/' + repo

    def run_link(item):
        return f'<a href="{base}/actions/runs/{item["run"]["id"]}">Run {item["run"]["id"]}</a>'

    def table(headers, rows):
        return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + escape(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'

    cards = []
    for severity, title in [('CRITICAL', 'Kritische Meldungen'), ('HIGH', 'Hohe Meldungen')]:
        before = str(previous['counts'][severity]) if previous else 'kein Vergleich'
        cards.append(f'<section class="card"><h3>{title}</h3><div class="value">{current["counts"][severity]}</div><p>Vorher: {before} · aktuell erfasster Main-Lauf</p></section>')
    unique = len({f['id'] for image in current['images'].values() for f in image['findings']})
    cards.append(f'<section class="card"><h3>Unterschiedliche CVE-IDs</h3><div class="value">{unique}</div><p>HIGH / CRITICAL über alle Images dedupliziert</p></section>')
    cards.append(f'<section class="card"><h3>Erfolgreiche Tests</h3><div class="value">{current["tests_passed"]}</div><p>Im zugehörigen Coverage-Bericht erfasst</p></section>')
    image_rows = []
    for service in SERVICES:
        image = current['images'][service]
        old = previous['images'][service] if previous else None
        cells = [escape(service)]
        for severity in ('CRITICAL', 'HIGH'):
            cells.append((str(old['counts'][severity]) + ' → ' if old else '') + str(image['counts'][severity]))
        cells.extend(str(image['counts'][s]) for s in ('MEDIUM', 'LOW', 'UNKNOWN', 'INFO'))
        cells.append(f'<details><summary>Image-ID &amp; Scan-Hash</summary><code>{image["image_id"]}</code><br><code>{image["scan_sha256"]}</code></details>')
        image_rows.append('<tr>' + ''.join('<td>' + c + '</td>' for c in cells) + '</tr>')
    groups = defaultdict(list)
    for service, image in current['images'].items():
        for finding in image['findings']:
            key = tuple(finding[k] for k in ('severity', 'id', 'package', 'installed_version', 'fixed_version'))
            groups[key].append(service)
    detail_rows = []
    for (severity, cve, package, installed, fixed), services in sorted(groups.items()):
        cve_text = escape(cve)
        if re.fullmatch(r'CVE-\d{4}-\d+', cve):
            cve_text = f'<a href="https://security-tracker.debian.org/tracker/{cve}">{cve_text}</a>'
        cells = [f'<span class="badge {"danger" if severity == "CRITICAL" else "warn"}">{severity}</span>', cve_text,
                 escape(package), escape(installed), escape(fixed or 'Im Scan nicht angegeben'),
                 escape(', '.join(sorted(set(services)))), str(len(services)), escape(assessment(package))]
        detail_rows.append(f'<tr data-security-row data-severity="{severity}">' + ''.join('<td>' + c + '</td>' for c in cells) + '</tr>')
    snapshot_path = f'status/measured-security-results/{repo.replace("/", "__")}/run-{current["run"]["id"]}-attempt-{current["run"]["attempt"]}.json'
    previous_text = run_link(previous) if previous else 'Kein früherer Main-Lauf erfasst'
    return f'''<section id="measured-security" class="viewer-section">
<div class="section-title"><h2>Container Security · echte Scan-Ergebnisse</h2>
<p>{escape(repo)} · Trivy-Container-Scans · Report-only</p></div>
<section class="panel"><p><strong>Governance-PASS bedeutet nicht schwachstellenfrei.</strong>
Offene Befunde sind keine Risikofreigabe. Die Zahlen zählen Image-/Paketmeldungen und können dieselbe CVE mehrfach enthalten.</p>
<p>Erfasster Stand: <strong>{escape(current['run']['updated_at'])}</strong> · {run_link(current)} ·
Commit <a href="{base}/commit/{current['run']['commit']}"><code>{current['run']['commit'][:12]}</code></a> · Versuch {current['run']['attempt']}.</p>
<p>Vergleich: {previous_text}. Ein gespeicherter Snapshot, keine Live-Abfrage. Neue Scans erscheinen nach erneutem Intake und Merge.</p></section>
<section class="cards">{''.join(cards)}</section>
<section class="panel"><h3>Betroffene Images und Vorher-/Nachher-Vergleich</h3>
{table(['Image', 'Kritisch: vorher → jetzt', 'Hoch: vorher → jetzt', 'Mittel jetzt', 'Niedrig jetzt', 'Unbekannt', 'Info', 'Identität'], image_rows)}
<p>Verglichen werden zwei Scan-Stände. Differenzen können auch durch geänderte Scanner-Daten entstehen; die verlinkte Bewertung beschreibt die Paketkorrekturen.</p></section>
<section class="panel"><h3>Bewertung und Nachweise</h3><p>Status: <strong>offen – technische Bewertung, keine Freigabe</strong>.</p>
<ul><li><a href="{base}/blob/main/docs/quality/CONTAINER_SECURITY_REMEDIATION.md">Dokumentierte Patch- und Restbefundbewertung</a></li>
<li><a href="https://github.com/joku-dev/devsecops-governance-framework/blob/main/{snapshot_path}">Zentral gespeicherter Snapshot mit Befunddetails</a></li>
<li>{run_link(current)}: originale Scan-/SBOM-Artefakte (zeitlich begrenzt aufbewahrt)</li></ul>
<p>Geprüft: GitHub-Run-Kontext, Rohdatei-Hashes gegen Producer-Manifeste und Image-Zuordnung.
Keine unabhängige Attestation und keine erneute Prüfung kompletter Image-/ZIP-Archive durch diesen Intake.</p></section>
<section class="panel"><details><summary><strong>Hohe und kritische Befunde anzeigen ({len(groups)} Paket-/Versionsgruppen)</strong></summary>
<div class="security-filters"><label>Schweregrad <select id="security-severity"><option value="all">Alle</option><option value="CRITICAL">Kritisch</option><option value="HIGH">Hoch</option></select></label>
<label>Suche <input id="security-search" type="search" placeholder="CVE, Paket oder Image"></label>
<span id="security-count" role="status" aria-live="polite"></span></div>
{table(['Schweregrad', 'CVE', 'Paket', 'Installiert', 'Korrigiert laut Scan', 'Images', 'Meldungen', 'Offene Prüfung'], detail_rows)}
</details></section></section>
<script>
(() => {{
 const select = document.getElementById('security-severity');
 const search = document.getElementById('security-search');
 const rows = Array.from(document.querySelectorAll('[data-security-row]'));
 function filter() {{
   let visible = 0;
   rows.forEach(row => {{
     const matches = (select.value === 'all' || row.dataset.severity === select.value) && row.textContent.toLowerCase().includes(search.value.toLowerCase());
     row.hidden = !matches; if (matches) visible++;
   }});
   document.getElementById('security-count').textContent = visible + ' / ' + rows.length + ' Gruppen sichtbar';
 }}
 select.addEventListener('change', filter); search.addEventListener('input', filter); filter();
}})();
</script>'''
