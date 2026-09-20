# Vertrauliches technisches Dossier — Forschungsstand 20. September 2026

Zweck: technische Unterlagen zur Vorbereitung einer möglichen Patentanmeldung.
Dies ist weder eine Anmeldung noch eine Feststellung von Neuheit, erfinderischer
Tätigkeit oder Schutzumfang. Rechtsraum und Anmeldestrategie sind noch offen.

## Technisches Problem

Zwischen der Prüfung einer Operation und ihrer Ausführung können sich ihre
Eingangsdaten, der akzeptierte Verlauf, Rollen oder die auswertende Implementierung
ändern. Eine Freigabe, die nur den Aktionsnamen identifiziert, beschreibt diesen
Kontext nicht vollständig. Das bestehende Repository adressiert bereits Teile
dieses Problems durch Request-Digests, Head-/Revisionsprüfungen, Providerprüfung
und dateiweises Binden der Betriebsimplementierung.

## Zu untersuchende Lösung

Ein deterministischer Replay erzeugt eine ausdrücklich definierte semantische
Zustandsprojektion. Drei getrennt typisierte und versionierte Commitments binden:

1. den vollständigen aufbewahrten Transaktionsverlauf;
2. den aktuellen für die Operation relevanten Zustand;
3. ein vollständig aufgezähltes Implementierungsmanifest.

Die konkrete Aktion, Rolle, das Profil und die Roots sind Bestandteile des
unveränderlichen Requests. Dessen Digest bindet die Erklärung. Unmittelbar vor
einer atomaren Veröffentlichung werden Verlauf und Zustand erneut gelesen,
die Commitments neu berechnet und die Erklärung nachgeprüft. Nur bei passenden
Voraussetzungen entsteht ein neues Transaktionsartefakt.

```text
aufbewahrter Verlauf -----> H
         | Replay --------> S
Implementierungsmanifest -> I
                             \
Aktion + Rolle + Profil + H/S/I -> Request-Digest -> persönliche Erklärung
                                                      |
                       erneute Prüfung unter Schreibsperre
                                                      |
                                atomare Testpublikation
```

Eine Korrektur referenziert einen früheren Request und bleibt nach anderen
Historienänderungen möglich. Historische Artefakte werden aufbewahrt, während
ihre aktuelle Wirksamkeit entfallen kann. Rücknahme beseitigt keine bereits
extern eingetretene Wirkung; der Prototyp hat deshalb genau einen lokalen Effekt.

## Nachweise und Zuordnung

| Behauptung im begrenzten Modell | Technischer Versuch/Nachweis |
|---|---|
| Unveränderter Kontext ermöglicht die Aktion | `unchanged`, tatsächliche Transaktionsdatei |
| Historie und semantischer Zustand sind unterscheidbar | `audit_only_history`, gleiche S-/verschiedene H-Roots |
| Neue relevante Evidenz verhindert alte Freigabe | `new_evidence` |
| Implementierungsbindung beeinflusst Zulässigkeit | `implementation_changed` und `implementation_without_binding` |
| Root-Prüfungen überschneiden sich mit vorhandenen Preconditions | `history_without_history_root` |
| Gleicher Zustand allein ersetzt die Historienbindung nicht | `history_without_history_preconditions` |
| Falsch angegebener Zustandsroot wird unabhängig erkannt | `state_root_changed` und `state_without_state_root` |
| Rolle, Profil, Aktionsinhalt und Erklärung bleiben gebunden | entsprechende Änderungsversuche |
| Eine Anfrage erzeugt keinen zweiten Effekt | `retry`, `concurrent_publication`, zwei lokale Prozesse |
| Widerruf bleibt nach neuer Historie wirksam | `revocation_after_change` |
| Gespeicherte Ergebnisse sind nachprüfbar | eigenständiger Replay-Prüfer, Manipulationstests |

## Vergleich und mögliche Abgrenzung

Die unveränderten bestehenden Pilot- und Betriebsabnahmetests werden im selben
Lauf ausgeführt und als Rohprotokolle aufbewahrt. Sie zeigen bereits vorhandene
Schutzmechanismen. Es handelt sich nicht um einen identischen End-to-End-
Benchmark zweier austauschbarer Produktionsimplementierungen.

Die Weglassversuche zeigen insbesondere, dass ein zusätzlicher History-Root
neben korrekt geprüften Historien-Heads teilweise redundant ist. Auch eine
deterministische Zustandsableitung ist durch ihre geprüften Eingaben bereits
gebunden. Ein expliziter State-Root macht diese Ableitung zusätzlich vergleichbar;
die Versuche behaupten keinen automatisch daraus folgenden neuen Schutz.

Als zu prüfende technische Merkmalskombination bleibt das gemeinsame Verfahren
aus getrennten Commitments, an konkrete Ausführungsimplementierung gebundener
Erklärung, erneuter Prüfung an der atomaren Schreibgrenze und nichtdestruktiver
Korrektur. Ob diese Kombination über bekannte Verfahren hinausgeht, muss eine
Recherche ermitteln. Einzelne Bausteine oder neue Bezeichnungen genügen nicht
als Nachweis von Neuheit oder erfinderischer Tätigkeit.

## Ausführbarkeit und Grenzen

Die genaue Ausgestaltung ist in DESIGN.md und im Code definiert; feste
Canonicalization-Testvektoren sowie Rohdaten erlauben Wiederholung. Der
Versuchsbereich verwendet bewusst nur einen Kontext und eine lokale Sperre.
Er demonstriert weder 1.500 Consumer noch Netzwerkdateisysteme oder verteilte
Transaktionen. Es handelt sich nicht um eine zertifizierte Sicherheitsprüfung.

Ein Implementation-Root identifiziert Dateien und Konfiguration. Er attestiert
weder die geladenen Maschineninstruktionen noch Betriebssystem, Hardware oder
kompromittierte Laufzeit. Das Bedrohungsmodell setzt diese Komponenten als
vertrauenswürdig voraus. Die Providerdaten der automatischen Versuche sind
synthetisch. Ein persönlich erklärter Lauf ist ein zusätzlicher Nachweis.

Die gespeicherten Zeitangaben und Git-Commits dokumentieren den Entwicklungsstand;
sie sind keine amtliche Prioritätssicherung. Fehlversuche und Grenzen sind Teil
der Unterlagen und dürfen für eine Präsentation nicht weggelassen werden.

## Unterlagen für eine anwaltliche Bewertung

* dieses Dossier, DESIGN.md, Quellstand und überprüfbares Evidence-Paket;
* genaue menschliche Beiträge und deren Entstehung, noch zu bestätigen;
* frühere öffentliche Versionen und Offenlegungszeitpunkte, noch zu ermitteln;
* Recherche zu relevanten Patenten und sonstigen Veröffentlichungen;
* beabsichtigte Anmelder, Rechteinhaber, Länder und Schutzstrategie.

Die DPMA-Hinweise verlangen eine hinreichend vollständige ausführbare technische
Beschreibung; der EPA-Leitfaden erläutert den technischen Beitrag bei Software.
Eine Patentanwältin oder ein Patentanwalt sollte diese Unterlagen früh prüfen.

Quellen, allgemein geprüft am 20. September 2026; keine vertraulichen Details
wurden als Suchanfrage an diese Stellen übermittelt:

* https://www.dpma.de/patente/anmeldung/index.html
* https://www.dpma.de/patente/patentschutz/schutzvoraussetzungen/index.html
* https://www.epo.org/en/news-events/in-focus/digital-innovations/patentability-digital-inventions
