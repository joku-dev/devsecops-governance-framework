# Live-Pilot: konkrete Entscheidungen vor der Anbindung

Status: **Rollen und Betriebsprofil am 13. September 2026 bestätigt; Live-Abnahme offen.** Die technische
Review-Ausnahme des Maintainers gilt für Implementierungs-PRs. Sie erteilt keine
Lifecycle-Behebungs-, Abschluss- oder Ausnahmefreigabe.

Die CLG-Testlaufzeit, Kennzahlen und der Viewer sind umgesetzt. Die zusätzlichen
DevSecOps-/Architektur-Adapter bereiten nachvollziehbare Eingabekandidaten vor.
Ihre Ausgaben bleiben ungeprüft und gelangen nicht in den akzeptierten Verlauf.
Die nächste Live-Anbindung benötigt die Entscheidungen aus dem
[Pilot-Entscheidungsblatt](governance-lifecycle-pilot-decisions.md).

## Bereits festgelegter erster Pilot

- Regel: GRS-002, `pull_request_review_required`.
- Repository: `joku-dev/devsecops-governance-framework`, Ressource `refs/heads/main`.
- Betriebsart: report-only.
- Keine künstlich erzeugte Live-Abweichung: Bei PASS wird kein offenes Finding
  erfunden. Fehler-, Behebungs- und Abschlussfolgen bleiben dann synthetische Tests.
- Der erste Live-Schritt nimmt Beobachtungen an; spätere Behebungs- und
  Abschlussentscheidungen brauchen zusätzlich eine überprüfbare menschliche
  Freigabe. Ein erfolgreicher Code-PR genügt dafür nicht.

## Bestätigt: Personen und Rollen (LD-01 / LD-03)

Der Maintainer hat die vorgeschlagene Mehrfachrolle mit „ja ich bestätige“
bestätigt. Alle drei Rollen sind für `joku-dev` (GitHub-ID `81616324`, öffentlicher
Anzeigename `joku`) im beschriebenen Piloten festgehalten:

| Rolle | Zuordnung |
|---|---|
| Behebungsentscheidung freigeben und widerrufen | `github-user:81616324` |
| Evidenzgebundenen Abschluss freigeben | `github-user:81616324` |
| Rollenbindungen verwalten und entziehen | `github-user:81616324` |

Die Mehrfachrolle ist ausdrücklich auf diesen Piloten begrenzt. Die
[versionierte Vorbereitung](governance-lifecycle-live-preparation.md) hält sie
getrennt von persönlichen Einzelfreigaben fest. Die Rollenbindung ist bestätigt;
die verifizierte Live-Rollenverwaltung bleibt Teil der technischen Abnahme.

## Noch offene Verifikation und Abnahme

Rollen, GitHub-Kanal als Umsetzungsrichtung und Betriebswerte sind bestätigt.
Der [persönliche GitHub-Kanaltest](governance-lifecycle-personal-channel.md) ist
mit dem persönlich abgegebenen Kommentar auf PR #87 erfolgreich nachgewiesen.
Die [aktionsbezogene Zustimmungsverifikation](governance-lifecycle-action-consent.md)
ist als getrennte Pilotvalidierung umgesetzt. Als nächste Schritte folgen der
begrenzte Betriebs-Publisher und die abschließende Betriebsabnahme.

| Entscheidung | Vorschlag | Folge / noch erforderlicher Nachweis |
|---|---|---|
| LD-02: bewusste, authentifizierte Zustimmung | Eigener Review eines unveränderlichen Entscheidungsdatensatzes mit Inhaltsdigest und erwarteter Finding-Revision | Kanal und persönliche Abgabe sind bestätigt. Der vorbereitete Kanaltest prüft Identität, Inhaltsdigest, Disposition und Widerruf. Die persönliche Erklärung ist verifiziert; die aktionsbezogene Pilotvalidierung bindet Entscheidungen, Fortschritt, Abschluss und Widerruf. Operative Annahme bleibt von LD-07 abhängig. |
| LD-07: Live-Abnahme | Zuerst lesenden Evidenz-Intake prüfen, danach Freigabe-/Widerrufs-/Abschluss-Negativfälle und Betriebs-Runbook abnehmen | Benannte Verantwortliche dokumentieren die Abnahme einschließlich Korrektur und Widerruf nach einem Abschluss. Erst anschließend Live-Aktivierung im bestätigten Umfang. |

## Was diese Entscheidung freigibt

Die Rollen sind bestätigt, der persönliche GitHub-Freigabekanal ist als
Umsetzungsrichtung bestätigt. Ein eigenes deaktiviertes Live-Profil liegt vor;
Provider-Verifikation und dauerhafte Pilotablage sind mit PR #87 umgesetzt; der persönliche Kanal ist mit PR #89 bestätigt. Die aktionsbezogene Verifikation liegt als eigene Pilotvalidierung vor. Das synthetische Profil wird dafür nicht
umgeschaltet oder umgeschrieben. Zunächst bleiben Live-Verarbeitung und
Veröffentlichung deaktiviert, bis die vereinbarten Prüfungen und Abnahme vorliegen.

CLG-06.4 braucht anschließend zugelassene Lifecycle-Consumer und eine definierte
Grundgesamtheit. Bestehende Consumer-Gesamtergebnisse oder mehrfach verwendete
Testidentitäten ergeben keine belastbare Lifecycle-Portfolioquote. Architektur-
Ausnahmen benötigen zusätzlich eine bestätigte Zuordnung ihrer Marker-/Regel-
Ziele zum Lebenszyklus; Gate-Nachrichten liefern diese Zuordnung nicht.

CLG-06.5 bleibt optional. Für einen funktionierenden Live-Piloten ist kein LLM
erforderlich. Diese optionale Erweiterung soll die Rollen- und Evidenzentscheidung
nicht verzögern.

## Bestätigt: Betriebsprofil für den ersten Live-Intake

Die Rollenbindung ist mit PR #85 gemergt. Der lesende Evidenzprüfer hat den
[echten Referenzlauf](../reference-runs/2026-09-13-clg-live-evidence-preflight.md)
mit zehn bestandenen Prüfungen erfasst und offline reproduziert. GRS-002 war
zum Beobachtungszeitpunkt PASS. Damit liegen konkrete Prüfergebnisse für die
Betriebsentscheidung vor. Der Maintainer hat das untenstehende Profil anschließend
mit „ja“ bestätigt; es ist in der [dauerhaften Pilotvalidierung](governance-lifecycle-durable-pilot-intake.md)
als eigene unveränderliche Version umgesetzt.

| Punkt | Bestätigtes Betriebsprofil | Konkrete Wirkung |
|---|---|---|
| LD-04: Trust-Wurzel und Producer | Authentifizierte GET-Abfragen der offiziellen GitHub.com-API plus die fünf im Vorbereitungsprofil festgelegten Producer-Dateien; nur erfolgreich abgeschlossener Mainline-Push, Versuch 1 | Andere Provider, veränderte Producer-Dateien, Branch-/PR-/manuelle/geplante Läufe und Wiederholungsversuche werden nicht zugelassen. Der GitHub-Provider ist die benannte Vertrauenswurzel; offline gespeicherte Metadaten allein begründen keine neue Vertrauensentscheidung. |
| LD-05: Frische und Zeitversatz | Höchstens 24 Stunden alte Beobachtung; kein zukünftiger Zeitversatz | Ältere Beobachtungen liefern keinen frischen Nachweis für eine neue Entscheidung oder einen Abschluss. Bestehende Historie bleibt erhalten. Ohne passenden neuen Mainline-Push kann die Evidenz veralten; es wird kein PASS erfunden und kein künstlicher Push erzeugt. |
| LD-04: Aufbewahrung | Vollständige Capture-Pakete, Akzeptanznachweise und Entscheidungsreferenzen während des Piloten unveränderlich aufbewahren; keine automatische Löschung, Aufbewahrungsentscheidung beim Pilotabschluss | Der künftige dauerhafte Pilot-Speicher muss vor Live-Annahme eingerichtet und getestet sein. Ein lokales `/tmp`-Paket oder GitHub-Artefakt mit Ablaufdatum reicht dafür nicht. Diese Freigabe wäre keine allgemeine Unternehmens-Aufbewahrungsrichtlinie. |
| LD-05: Replay und Konflikte | Gleiche Herkunftsidentität plus gleicher Inhalt ist eine Wiederholung ohne neue Wirkung; abweichender Inhalt bei gleicher Identität wird quarantänisiert | Keine Überschreibung akzeptierter Evidenz; Live-Speicher, konkurrierende Annahme und vollständige Konfliktprüfung müssen dies vor Aktivierung nachweisen. |

Die Bestätigung ist erfasst. Das konkrete Betriebsprofil und die dauerhafte
Pilot-Speicherung sind umgesetzt. Danach folgen die inhaltsgebundene persönliche
Freigabeverifikation und der vollständige Betriebsnachweis. Die separate
Live-Abnahme (LD-07) bleibt bis zur Vorlage dieses Nachweises offen. Persönliche
Behebungs- und Abschlussfreigaben werden weiterhin vom benannten Menschen
selbst erteilt.
