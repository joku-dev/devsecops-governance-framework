# Live-Pilot: konkrete Entscheidungen vor der Anbindung

Status: **Entscheidungsvorlage, keine Live-Freigabe.** Die technische
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

## Zuerst erforderlich: Personen und Rollen (LD-01 / LD-03)

Diese Felder können nicht aus Repository-Adminrechten oder einem Tool-Login
abgeleitet werden. Sie sind vor Umsetzung der verbindlichen Rollenbindung vom
Maintainer mit den zuständigen Governance-Verantwortlichen zu bestätigen.

| Rolle im begrenzten Piloten | Benötigte Angabe | Status |
|---|---|---|
| Behebungsentscheidung freigeben und widerrufen | Name, authentifiziertes Konto, freigegebener Geltungsbereich | Offen |
| Evidenzgebundenen Abschluss freigeben | Name, authentifiziertes Konto, freigegebener Geltungsbereich | Offen |
| Rollenbindungen verwalten und entziehen | Name, authentifiziertes Konto, Zuständigkeit für Änderungen | Offen |

Der technische Vertrag trennt die Rollen. Ob dieselbe Person mehrere Rollen
übernehmen darf, muss die verantwortliche Stelle für diesen Piloten ausdrücklich
festhalten; die Implementierung erfindet weder eine neue Trennungspflicht noch
eine Ausnahme davon. Waiver-Autoritäten werden nicht automatisch auf diese
Rollen übertragen.

## Weitere entscheidungsreife Vorschläge

Die folgenden Vorschläge sind konkrete Ausgangspunkte, keine angenommenen
Genehmigungen. Ihre Umsetzung kann nach der Rollenentscheidung abgegrenzt werden.

| Entscheidung | Vorschlag | Folge / noch erforderlicher Nachweis |
|---|---|---|
| LD-02: bewusste, authentifizierte Zustimmung | Eigener Review eines unveränderlichen Entscheidungsdatensatzes mit Inhaltsdigest und erwarteter Finding-Revision | Provider-Adapter prüft Identität, genaue Review-Revision, Disposition und Widerruf. Bot-/Tool-Aktionen dürfen keine menschliche Zustimmung vortäuschen. Freigabekanal und Umgang mit Werkzeugnutzung ausdrücklich bestätigen. |
| LD-04: erste Evidenzquelle | Self-Security-Workflow `governance-repository-security.yml` dieses Repositorys, Mainline-Push, Artefakt `governance-repository-security` | Producer, Workflowrevision, voller Commit, Lauf/Versuch, Artefaktzugehörigkeit, Digest und Baseline unabhängig überprüfen; Trust-Wurzeln und Aufbewahrung bestätigen. Diagnose-, PR- und Branch-Läufe bleiben getrennt. |
| LD-05: Frische und Replay | Die bisherigen Testwerte 24 Stunden / kein zukünftiger Zeitversatz als zu prüfenden Startpunkt verwenden | Verantwortlich bestätigte Betriebswerte anhand tatsächlicher Laufhäufigkeit; keine automatische Übernahme als SLA oder Produktionspolicy. Replay-/Konfliktbehandlung bleibt explizit. |
| LD-07: Live-Abnahme | Zuerst lesenden Evidenz-Intake prüfen, danach Freigabe-/Widerrufs-/Abschluss-Negativfälle und Betriebs-Runbook abnehmen | Benannte Verantwortliche dokumentieren die Abnahme einschließlich Korrektur und Widerruf nach einem Abschluss. Erst anschließend Live-Aktivierung im bestätigten Umfang. |

## Was diese Entscheidung freigibt

Nach bestätigten Rollen und Freigabekanal lässt sich ein eigener Live-Profil- und
Provider-Adapter-PR konkret umsetzen. Das synthetische Profil wird dafür nicht
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
