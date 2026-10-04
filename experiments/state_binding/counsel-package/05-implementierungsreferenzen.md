# 5 Implementierungsreferenzen und Nachweise

## 5.1 Was tatsächlich implementiert ist

Die hier beschriebene vollständige lokale Ausführungsform ist im privaten Forschungsbereich `experiments/state_binding/` implementiert. Referenzstand dieser Unterlage ist Commit `56ed0c743121fddc9d117b69eb470493dff5046d` im Repository `joku-dev/devsecops-governance-framework`. Dieser Commit enthält den persönlichen Demonstrationsnachweis. Die gebundenen Python-Quelldateien sind gegenüber dem ursprünglichen Prototyp-Commit unverändert.

Es wird keine weitere Installation derselben vollständigen Lösung bei Dritten behauptet. Das Consumer-Repository `ha-CPsWMS` ist ein Ziel des bestehenden Governance-Frameworks, aber kein Nachweis einer dort bereits integrierten H-/Z-/I-Prototypausführung. Die KI- und Agentenanwendungen in Kapitel 4 sind ebenfalls Übertragungsentwürfe.

Das Weitergabepaket enthält einen gezielten Quellcodeauszug mit den gebundenen Implementierungsdateien und den Prototyptests sowie die originalen Evidence-Pakete. Der Auszug ist zur Offline-Inspektion bestimmt. Er ersetzt nicht den vollständigen Repository-Checkout für die Gesamttests. Der eigenständige Prüfer des automatisierten Evidence-Pakets benötigt lediglich die Python-Standardbibliothek.

## 5.2 Feste Codefundstellen

Die Links in dieser Tabelle sind auf den oben genannten Commit festgelegt und benötigen Zugriff auf das private Repository. Alle angegebenen Python-Dateien sind außerdem im Quellcodeauszug enthalten.

| Funktion | Implementierte Stelle | Bezugsmerkmale |
|---|---|---|
| Historie und Zustand getrennt binden | [prototype.py Zeile 102](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L102), `history_payload`, `state_payload`, `roots` | M1, M2 |
| Implementierungsmanifest und Root | [prototype.py Zeile 114](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L114), `source_manifest`, `implementation_manifest` | M3 |
| Antrag und Vorbedingungen | [prototype.py Zeile 144](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L144), `validate_request`, `preconditions`, `prepare` | M4 |
| Replay und Zustandsübergänge | [prototype.py Zeile 179](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L179), `reduce_event`, `replay` | M1, M7 |
| Erneute Prüfung und Publikation | [prototype.py Zeile 338](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L338), `execute` | M5, M6 |
| Angehängter synthetischer Widerruf | [prototype.py Zeile 370](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/prototype.py#L370), `revoke` | M7 |
| Lokale Sperre und atomarer Writer | [store.py Zeile 14](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/scripts/lib/governance_lifecycle/store.py#L14), `writer_lock`, `publish_transaction` | M6; bestehender Baustein |
| Persönlicher Demo-Adapter | [human_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/human_demo.py), `prepare`, `execute` | M4, M5 |
| Prüfung der GitHub-Erklärung | [personal_probe.py Zeile 42](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/scripts/lib/governance_lifecycle/personal_probe.py#L42), `assess_bound_comments`, `collect_bound` | M5; bestehender Baustein |
| Versuche und eigener Evidence-Prüfer | [run_experiments.py](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/run_experiments.py) und [verify_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/experiments/state_binding/verify_evidence.py) | Experimentelle Überprüfung |
| Automatische Testfälle | [test_state_binding_prototype.py](https://github.com/joku-dev/devsecops-governance-framework/blob/56ed0c743121fddc9d117b69eb470493dff5046d/tests/test_state_binding_prototype.py) | 17 zusätzliche Testmethoden |

## 5.3 Aufbewahrte Versuche

Der automatisierte Lauf umfasst 18 tatsächliche lokale Dateisystemversuche. Der Runner prüft nicht nur Rückgabewerte, sondern auch die Anzahl und den Inhalt der Transaktionen vor und nach dem jeweiligen Versuch. Der Konkurrenzversuch verwendet zwei verschiedene Prozesse. Alle automatisierten Providererklärungen sind synthetisch und als solche ausgewiesen.

| Versuch | Ergebnis | Ausgelassene Prüfungen | Status |
|---|---|---|---|
| `unchanged` | Publiziert | Keine | PASS |
| `new_evidence` | Zurückgewiesen | Keine | PASS |
| `audit_only_history` | Zurückgewiesen | Keine | PASS |
| `implementation_changed` | Zurückgewiesen | Keine | PASS |
| `role_changed` | Zurückgewiesen | Keine | PASS |
| `profile_changed` | Zurückgewiesen | Keine | PASS |
| `action_changed` | Zurückgewiesen | Keine | PASS |
| `provider_revoked` | Zurückgewiesen | Keine | PASS |
| `provider_edited` | Zurückgewiesen | Keine | PASS |
| `provider_deleted` | Zurückgewiesen | Keine | PASS |
| `state_root_changed` | Zurückgewiesen | Keine | PASS |
| `implementation_without_binding` | Publiziert | implementation | PASS |
| `history_without_history_root` | Zurückgewiesen | history | PASS |
| `history_without_history_preconditions` | Publiziert | history, head, revision | PASS |
| `state_without_state_root` | Publiziert | state | PASS |
| `retry` | 1 Publikation; Wiederholung abgewiesen | Keine | PASS |
| `revocation_after_change` | Widerruf wirksam; Historie erhalten | Keine | PASS |
| `concurrent_publication` | 2 Prozesse; 1 Publikation | Keine | PASS |

Das Ergebnis ist **18 von 18 erwartungsgemäß bestandenen Versuchen**. Eine erwartete Zurückweisung zählt als bestandener Negativtest. Eine im Weglassversuch absichtlich zugelassene Publikation ist ebenfalls ein erwartetes Experimentergebnis; sie ist keine produktive Freigabe und kein versehentlich akzeptierter Sicherheitsbefund.

Zusätzlich sind 27 unveränderte Tests des vorhandenen Pilot-Aktions- und Betriebsabnahmecodes als Vergleich ausgeführt worden. Sie sind kein identischer End-to-End-Benchmark zweier austauschbarer Produkte. Die vollständige Repository-Validierung nach dem persönlichen Lauf bestand mit 640 Tests. OPA, Runtime-, Repository- und Provenance-Prüfungen waren erfolgreich. Die Prototyptests sind in diesen 640 Tests enthalten, nicht zusätzlich zu addieren.

## 5.4 Erkenntnisse aus Weglassversuchen

Wird ausschließlich die zusätzliche History-Root-Prüfung weggelassen, verhindert die bestehende Head-/Sequenzprüfung weiterhin die Publikation auf einer geänderten Historie. Erst das Weglassen aller drei Historienvorbedingungen im betreffenden Versuch lässt die geänderte Historie bei unverändertem definierten Zustand zu. Dies belegt eine Überschneidung vorhandener Schutzmechanismen.

Wird die Implementierungsbindung weggelassen, kann eine nach der Freigabe geänderte Ausführungskonfiguration verwendet werden. Die normale Bindungsprüfung weist denselben Fall zurück. Eine weitere Versuchspaarung prüft einen bewusst falsch angegebenen State-Root bei ansonsten passenden Daten. Diese Versuche zeigen den Einfluss der jeweiligen Prüfung, begründen aber keinen automatischen Neuheits- oder Überlegenheitsnachweis gegenüber anderen korrekt implementierten Verfahren.

## 5.5 Persönlicher Demonstrationslauf

Am 20. September 2026 gab das benannte Konto `joku-dev`, GitHub-ID `81616324`, die antragsgebundene Erklärung selbst in [PR-Kommentar 5749239832](https://github.com/joku-dev/devsecops-governance-framework/pull/176#issuecomment-5749239832) ab. Der Ausführungsprozess erfasste und prüfte sie um `10:33:43 UTC`. Er veröffentlichte genau ein lokales Artefakt mit dem Inhalt `Personally authorized PRIVATE LOCAL TEST artifact`.

Die Erfassung blieb zusammen mit dem Antrag und dem Artefakt in der Transaktion erhalten. Eine erneute direkte Providerabfrage um `10:35:21 UTC` bestätigte dieselbe Erklärung. Die nachfolgende Offline-Prüfung rekonstruierte Kette und Zustand. Eine rein lesende Wiederverwendungsprüfung wies den alten Antrag wegen `stale_history` zurück; es wurde kein zweiter persönlicher Ausführungsversuch gestartet.

Der personenbezogene Nachweis umfasst die vom Provider bestätigte Kontoidentität und die ausdrückliche Selbsterklärung. Er ist keine Hardware- oder Anwesenheitsattestierung. Die Beobachtung und innere Fixture-Freigabe bleiben synthetisch. Die GitHub-Erfassung ist eine zeitbezogene Beobachtung und keine permanente Zusage über den späteren Zustand des Kommentars.

| Kennung | Wert |
|---|---|
| Äußerer Antragsdigest | `48a97c11dd0fe4f74806f95d2fcd2af019b097d3e129f0a18a9774654ec7ce88` |
| Publikation ohne Präfix `transaction:` | `b7d3992989486569612bf055cd04af5b25e9d01a8ee8dd776baf79ff82796ed4` |
| Code-Stand der persönlichen Ausführung | `4dbc458872d39c113d8f0b978aab918eb0c6ce28` |

## 5.6 Integrität und Wiederholbarkeit

| Datei | SHA-256 des unveränderten Pakets |
|---|---|
| `run-001.zip` | `919e299760d1f62d4345ff7a239ef7919c82d23c2c36732d9b8a1d7b665f29ea` |
| `personal-demo-001.zip` | `2183f4a4601b5f96cadd2a649c0ca601ea3f16d4e5305dd5fa47a8c1bc12a38d` |

Der eigenständige Prüfer des automatisierten Pakets importiert die Prototypimplementierung nicht. Er rekonstruiert Historie, Zustandsprojektion, Roots und zulässige Effekte selbst. Das persönliche Paket wird dagegen mit dem vorhandenen Replay- und Providerprüfcode geprüft. Diese unterschiedliche Unabhängigkeit ist bei der Bewertung der Beweiskraft zu berücksichtigen.

Nach Entpacken des Weitergabepakets lässt sich der automatische Nachweis ohne GitHub-Zugang und ohne neue persönliche Erklärung prüfen:

```bash
python3 source/experiments/state_binding/verify_evidence.py \
  evidence/run-001.zip \
  --expect-manifest-sha256 \
  e8a903751e3e3f040371329f8f8ef2910376f72decd42a033f3620b50caf4628
```

Eine Wiederholung der vollständigen Versuche erfolgt im vollständigen Repository-Checkout gemäß `experiments/state_binding/README.md`. Das Nachvollziehen gespeicherter Daten erfordert keine neue Erklärung. Eine weitere tatsächliche persönliche Testaktion benötigt einen neuen Antrag und die dazu passende Erklärung.

Dateihashes und signierte Entwicklungscommits binden Bytes an einen dokumentierten Bezugspunkt. Sie ersetzen keine amtliche Zeitbestätigung und beweisen nicht den Zeitpunkt einer Erfindung. Das zusätzliche `MANIFEST.json` des Weitergabepakets erlaubt die Prüfung aller enthaltenen Dateien.

## 5.7 Hosted CI und produktiver Reifegrad

Die dokumentierte letzte vollständig ausgewertete PR-Revision `4dbc458` bestand Governance CI und Repository Security. Dependency Review war in der Repositorykonfiguration nicht verfügbar; der Consumer Lifecycle Guard erhielt HTTP 404 für eine bestehende Providerdiskussion; CodeQL scheiterte am Zugriff auf die Workflow-Run-API. Die Detailreferenzen liegen in `evidence/CI-LIMITATIONS.md`.

Der private PR #176 ist ein Draft. Der lokale Funktionsnachweis ist abgeschlossen; daraus wird keine Aussage abgeleitet, dass alle Hosted-Checks grün sind oder eine produktive Einführung freigegeben ist. Spätere PR-Zustände sind von diesem festgehaltenen Nachweisstand zu unterscheiden.

## 5.8 Externe technische Referenzen und Vergleichsbausteine

Die folgenden öffentlichen Primärquellen wurden am 20. September 2026 geprüft. Sie erläutern bekannte Problemklassen und verwandte Mechanismen. Die Auswahl ist keine vollständige Patentrecherche. Die Aussagen über den vorliegenden Prototyp stützen sich auf dessen Code und Versuche; die externen Referenzen belegen keine identische Drittimplementierung der gesamten Lösung.

**[E1] MITRE CWE 367.** Beschreibt Zustandsänderungen zwischen Prüfung und Nutzung einer Ressource sowie die Bedeutung geeigneter Synchronisation. Bezug: bekannte TOCTOU-Problemklasse. https://cwe.mitre.org/data/definitions/367.html

**[E2] RFC 8785 JSON Canonicalization Scheme.** Beschreibt eine standardisierte kanonische JSON-Darstellung für wiederholbare kryptografische Operationen. Bezug: bekannte Kanonisierung. Der Prototyp verwendet einen eigenen eingeschränkten Vertrag. https://www.rfc-editor.org/rfc/rfc8785

**[E3] RFC 9162 Certificate Transparency Version 2.0.** Beschreibt Merkle-Bäume sowie Inklusions- und Konsistenznachweise für Logs. Bezug: bekannte kryptografische Historienbindung. Der Prototyp verwendet eine Hashkette und implementiert kein Certificate-Transparency-Log. https://www.rfc-editor.org/rfc/rfc9162

**[E4] in-toto.** Dokumentiert ein implementiertes Framework zur Prüfung von Softwarelieferketten mit definierten Schritten, autorisierten Beteiligten und Artefaktbeziehungen. Bezug: bekannte Bindung technischer Artefakte und Prozessnachweise. Die vollständige lokale H-/Z-/I-Freigabekombination dieses Pakets wird daraus nicht abgeleitet. https://in-toto.io/docs/what-is-in-toto/

**[E5] LangGraph Interrupts.** Dokumentiert ein implementiertes Unterbrechungs- und Wiederaufnahmemodell für menschliche Eingaben sowie Anforderungen an Seiteneffekte beim erneuten Ausführen von Knoten. Bezug: bekannte Freigabepausen in Agentenabläufen. Es besteht keine implementierte Anbindung an diesen Prototyp. https://docs.langchain.com/oss/python/langgraph/interrupts

**[E6] RFC 9396 OAuth 2.0 Rich Authorization Requests.** Beschreibt strukturierte `authorization_details` für differenzierte Autorisierungsanfragen. Bezug: bekannte explizite Beschreibung erlaubter Aktionen und Ressourcen. Der Prototyp implementiert weder OAuth noch diesen RFC. https://www.rfc-editor.org/rfc/rfc9396

Eine Neuheitsbewertung müsste konkrete Veröffentlichungen und deren Zeitpunkte mit den einzelnen technischen Merkmalen vergleichen. Insbesondere dürfen Hashketten, explizite Aktionsfreigaben, Versionsvergleiche, Implementierungsmanifeste und atomare Schreibverfahren nicht allein aufgrund anderer Bezeichnungen als neue Verfahren behandelt werden.
