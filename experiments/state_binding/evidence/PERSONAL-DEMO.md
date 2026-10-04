# Persönlicher Demonstrationslauf — erfolgreich ausgeführt

Am 20. September 2026 hat der Prototyp die von `joku-dev` persönlich abgegebene
[Erklärung in PR #176](https://github.com/joku-dev/devsecops-governance-framework/pull/176#issuecomment-5749239832)
direkt bei GitHub geprüft und genau eine lokale Testpublikation ausgeführt.
Der Repository-Status wurde vor der Ausführung und vor der erneuten Erfassung
als privat bestätigt.

| Nachweis | Ergebnis |
|---|---|
| Benanntes Konto | `joku-dev`, `github-user:81616324` |
| Geprüfter Antrag | [Unveränderter Antrag](personal-demo-request.json) |
| Erklärungsvorlage | [Ursprünglicher Textentwurf](personal-demo-statement.txt); die tatsächlichen Providerdaten liegen im Paket |
| Code-Stand der Ausführung | `4dbc458872d39c113d8f0b978aab918eb0c6ce28`; alle gebundenen Quelldateien stimmen überein |
| Providererfassung während der Ausführung | `2026-09-20T10:33:43Z`, `confirmed` |
| Erneute direkte Providerabfrage | `2026-09-20T10:35:21Z`, `confirmed`; ursprüngliche Erklärung unverändert vorhanden |
| Aufbewahrte Transaktionen | 1 synthetische Beobachtung + 1 persönliche Testpublikation |
| Testinhalt | `Personally authorized PRIVATE LOCAL TEST artifact` |
| Replay | Kette, H-/S-/I-Roots, Aktionsbindung und gespeicherte Erklärung konsistent |
| Wiederverwendung des Antrags | Rein lesende Vorbedingungsprüfung lehnt mit `stale_history` ab; keine zweite Ausführung versucht |

Antragsdigest: `48a97c11dd0fe4f74806f95d2fcd2af019b097d3e129f0a18a9774654ec7ce88`.

Publikation: `transaction:b7d3992989486569612bf055cd04af5b25e9d01a8ee8dd776baf79ff82796ed4`.

## Aufbewahrte Dateien

[personal-demo-001.zip](personal-demo-001.zip) enthält die tatsächlichen
Workspace-Dateien ohne lokale Sperrdatei, beide Transaktionsdateien mit der
Providererfassung, die erneute Providerabfrage, das Quellmanifest, den Prüfbericht
und ein Manifest aller Paketdateien. Der Vorzustand wurde aus dem unveränderten
Historienpräfix rekonstruiert; er ist keine zusätzliche Vorher-Momentaufnahme.
Die GitHub-Antworten enthalten keine Zugangsdaten. Das gesamte Paket bleibt privat.

Das [Prüfergebnis](personal-demo-verification.json) hält zusätzlich die Paketdigests
und die anschließende [Repository-Validierung](personal-demo-validation.log)
fest. Das automatisierte Paket `run-001.zip` bleibt unverändert.

Manifest SHA-256: `50f3c008b7b218dd8252a05a47b30f133010ad26bbcbe5392fa8c9e3ffd5b950`

ZIP SHA-256: `2183f4a4601b5f96cadd2a649c0ca601ea3f16d4e5305dd5fa47a8c1bc12a38d`

## Offline erneut prüfen

Vom Repository-Root mit vorbereiteter Validierungsumgebung ausführen. Der Befehl
liest das Archiv ohne Entpacken oder erneute Publikation. Er nutzt den vorhandenen
Replay-Code; er ist kein unabhängig implementierter Prüfer und keine aktuelle
GitHub-Abfrage.

```bash
.venv-validation/bin/python - <<'PY'
from pathlib import Path
import hashlib, json, zipfile
from experiments.state_binding import prototype as p
from lib.governance_lifecycle.personal_probe import assess_bound_comments, replay_bound_snapshot

base = Path('experiments/state_binding/evidence')
data = (base / 'personal-demo-001.zip').read_bytes()
assert hashlib.sha256(data).hexdigest() == '2183f4a4601b5f96cadd2a649c0ca601ea3f16d4e5305dd5fa47a8c1bc12a38d'
with zipfile.ZipFile(base / 'personal-demo-001.zip') as z:
    raw = z.read('MANIFEST.json')
    assert hashlib.sha256(raw).hexdigest() == '50f3c008b7b218dd8252a05a47b30f133010ad26bbcbe5392fa8c9e3ffd5b950'
    manifest = json.loads(raw)
    assert len(z.namelist()) == len(set(z.namelist()))
    assert set(z.namelist()) == set(manifest) | {'MANIFEST.json'}
    assert all(hashlib.sha256(z.read(n)).hexdigest() == d for n, d in manifest.items())
    txs = [json.loads(z.read(n)) for n in sorted(manifest)
           if n.startswith('workspace/ledger/transactions/')]
    assert len(txs) == 2 and [t['event']['kind'] for t in txs] == ['evidence', 'publish']
    state = p.replay(txs)
    request = json.loads(z.read('workspace/personal-request.json'))
    assert p.digest(request) == '48a97c11dd0fe4f74806f95d2fcd2af019b097d3e129f0a18a9774654ec7ce88'
    body = txs[-1]['event']['body']
    p.validate_human_capture(body['human_capture'], request['prototype_grant'])
    assert body['omitted_checks'] == []
    assert state['publication']['artifact'] == body['artifact']
    recheck = json.loads(z.read('provider-recheck.json'))
    p.validate_human_capture(recheck, request['prototype_grant'])
    assert replay_bound_snapshot(recheck, assessor=assess_bound_comments)['status'] == 'confirmed'
print('Paketintegrität, persönlicher Nachweis und genau eine Testpublikation bestätigt.')
PY
```

## Aussagegrenze und neuer Lauf

Das Konto und seine ausdrückliche Erklärung sind über GitHub geprüft; körperliche
Anwesenheit ist selbst erklärt und nicht durch den Provider attestiert. Die
Beobachtungen und innere Fixture-Freigabe bleiben synthetische Testdaten.
`official_state=false`: Der Lauf erteilt keine Produktions-, Deployment-,
Betriebsabnahme- oder Patentfreigabe. Eine spätere Änderung der Providerdaten
wird durch diesen historischen Nachweis nicht ausgeschlossen.

Die Erklärung wurde von der benannten Person abgegeben; Codex hat sie nicht
stellvertretend gepostet. Der Antrag ist durch die Publikation verbraucht.
Für eine weitere Aktion einen neuen Workspace und einen neuen Antrag gemäß
[README](../README.md#persönlicher-demonstrationslauf) erstellen. Jede weitere
persönliche Demonstration benötigt eine dazu passende neue Erklärung.
