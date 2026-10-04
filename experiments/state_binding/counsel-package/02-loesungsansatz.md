# 2 Lösungsansatz

## 2.1 Kerngedanke

Die Lösung bildet drei getrennte kryptografische Commitments über die validierte Historie, eine deterministische Zustandsprojektion und ein explizites Implementierungsmanifest. Ein unveränderlicher Antrag enthält diese Commitments zusammen mit der konkreten Aktion, ihrem Inhalt, dem Geltungsbereich und den maßgeblichen Rollen- und Profilwerten. Die Zustimmung referenziert den Digest dieses vollständigen Antrags.

Vor der Publikation lädt das System den maßgeblichen Kontext erneut, rekonstruiert den Zustand und berechnet die Commitments erneut. Es prüft außerdem die aktuelle Erklärung des zuständigen Providers. Jede im Vertrag relevante Abweichung verhindert die Publikation. Im lokalen Prototyp bleiben diese Prüfungen und die Publikation innerhalb einer exklusiven Schreibsperre. Der veröffentlichte Inhalt ist Teil derselben atomar sichtbaren Transaktionsdatei.

## 2.2 Begriffe und Bindungsfunktion

| Symbol | Bedeutung |
|---|---|
| L | Geordnete, validierte Transaktionshistorie |
| S | Durch deterministischen Replay von L erzeugter Zustand |
| M | Vollständig aufgezähltes Manifest der ausgewählten Implementierungsdateien |
| H | Digest des typisierten History-Commitments |
| Z | Digest des typisierten State-Commitments; im Code `roots.state` |
| I | Digest des typisierten Implementation-Commitments |
| A | Vollständiger konkreter Aktionskörper |
| Q | Antrag mit A, H, Z, I, Geltungsbereich, Rolle, Profil, Head und Sequenz |
| D | Kanonischer SHA-256-Digest des Antrags Q |

In der Literatur werden sowohl Zustandsobjekte als auch deren Hashwerte häufig mit S bezeichnet. Dieses Paket verwendet Z für den Zustandsdigest, um beide Größen auseinanderzuhalten. Die Implementierung verwendet die Feldnamen `history`, `state` und `implementation`.

Die folgende Darstellung beschreibt die Datenbeziehungen, nicht eine zusätzliche Protokollschicht:

```text
S = Replay(L)
H = SHA256(Canonical(HistoryEnvelope(L)))
Z = SHA256(Canonical(StateEnvelope(S)))
I = SHA256(Canonical(ImplementationEnvelope(M)))
D = SHA256(Canonical(Q(A, H, Z, I, Rolle, Profil, Head, Sequenz)))
```

Das Commitment ist eine Bindung an Daten relativ zum verwendeten Hashverfahren. Es ist weder eine Verschlüsselung noch für sich genommen eine digitale Unterschrift oder ein Identitätsnachweis.

## 2.3 Ablauf vom Antrag bis zum Effekt

1. Der Antragsersteller liest unter lokaler Schreibsperre die Historie und prüft ihre Struktur, Reihenfolge und Inhaltsreferenzen.
2. Ein deterministischer Replay erzeugt den aktuellen Zustand. Der Commitment-Baustein berechnet H, Z und I.
3. Der Antragsersteller fixiert Aktion, Inhalt und alle Kontextwerte. Nach der Vorbereitung wird die Sperre freigegeben; die menschliche Prüfung kann zeitlich getrennt stattfinden.
4. Eine benannte Person erklärt ihre Zustimmung zu einem Antragsdigest über den vorgesehenen Provider. Im persönlichen Demonstrationslauf ist dies ein GitHub-Kommentar mit einer ausdrücklichen Selbsterklärung.
5. Der Ausführungsprozess erwirbt erneut die lokale Schreibsperre. Er lädt und prüft den vollständigen aktuellen Kontext sowie den gespeicherten Antrag.
6. Der Prozess liest die Providerdaten frisch ein, prüft ihre Inhalts- und Identitätsbindung und liest den lokalen Kontext anschließend nochmals. Die Sperre bleibt gehalten.
7. Nur wenn alle vorgeschriebenen Prüfungen bestehen, veröffentlicht der Writer eine neue Transaktionsdatei mit dem Testinhalt und den gespeicherten Nachweisen.
8. Die neue Transaktion verändert die Historie. Ein erneuter Versuch mit dem alten Antrag findet deshalb einen abweichenden Kontext und erzeugt keine weitere Publikation.

## 2.4 Technische Wirkung im belegten Modell

**Kontextabweichungen werden vor dem lokalen Effekt erkannt.** Die Versuche zeigen Zurückweisungen nach neuer Evidenz, geänderter Konfiguration, Rollen- und Profilwechseln sowie Änderungen der Test-Providererklärung.

**Historie und definierter Zustand sind getrennt vergleichbar.** Eine Auditnotiz kann H verändern, während Z unverändert bleibt. Vertrag 1 bindet trotzdem strikt an die neue Historie und verwirft den alten Antrag.

**Die geprüfte Aktion entspricht dem gespeicherten Effekt.** Der Aktionsinhalt im Antrag muss dem Inhalt des veröffentlichten Artefakts entsprechen. Der Writer schreibt das Artefakt direkt in die Transaktion; ein späterer ungebundener zweiter Schreibaufruf entfällt für diesen Demonstrationseffekt.

**Konkurrierende lokale Ausführungen werden serialisiert.** Zwei Prozesse verwenden dieselbe Sperre. Der erste erfolgreiche Prozess verändert den Kontext, bevor der zweite seine aktuelle Prüfung abschließen kann. Der Nachweis betrifft höchstens eine Publikationsdatei für denselben Antrag in diesem Ledger.

**Historische Nachweise bleiben bei Korrekturen erhalten.** Im synthetischen Widerrufsversuch wird eine Korrektur angehängt. Die Zustandsprojektion entfernt die aktuelle Wirksamkeit der früheren Publikation, ohne deren historische Datei zu löschen.

## 2.5 Zu untersuchende technische Merkmalskombination

Für die anwaltliche Untersuchung lässt sich der technische Gegenstand in sieben Merkmale zerlegen. Diese Aufstellung ist eine Analysehilfe und kein ausformulierter Patentanspruch.

| Merkmal | Konkretisierung im Prototyp |
|---|---|
| M1 | Validierte, inhaltsadressierte Historie und deterministischer Replay |
| M2 | Unterschiedlich typisierte Commitments für Historie und festgelegten Zustand |
| M3 | Separates Commitment über ein vollständig aufgezähltes Implementierungsmanifest |
| M4 | Gemeinsame Bindung von Aktion, Commitments, Rolle, Profil, Head und Sequenz im Antrag |
| M5 | Frische Providerprüfung und erneutes Lesen des lokalen Kontexts vor der Publikation |
| M6 | Gemeinsame lokale Sperre und atomare Veröffentlichung des eigentlichen Testinhalts |
| M7 | Angehängte Korrektur mit historischer Erhaltung und geänderter aktueller Wirksamkeit |

Die Hashfunktion, Hashketten, deterministische Serialisierung, Sperren und strukturierte Freigaben sind bekannte Bausteine. Welche Kombination nach dem relevanten Stand der Technik überhaupt abgrenzbar ist, bleibt Gegenstand der Recherche. Die Unterlagen machen keine Aussage, dass sämtliche Merkmale für einen möglichen Anspruch erforderlich, neu oder erfinderisch sind.

## 2.6 Varianten und noch nicht implementierte Ausgestaltungen

Der Mechanismus ist grundsätzlich von GitHub und von einem Governance-Befund als Fachobjekt trennbar. Andere Provider könnten einen Antrag über eine interne Freigabeanwendung, eine Signaturinfrastruktur oder eine dafür zugelassene Maschinenidentität bestätigen. Dafür wäre jeweils ein eigener überprüfter Providervertrag erforderlich.

Ein Datenbank-Adapter könnte dieselbe Bindungsprüfung innerhalb einer Transaktion mit Versionsprüfung ausführen. Für externe Effekte kommen beispielsweise bedingte Zieloperationen, Fencing-Tokens oder eine Outbox mit idempotentem Empfänger in Betracht. Diese Begriffe beschreiben mögliche nächste Ausführungsformen; ihre Korrektheit und Kombination sind im vorliegenden Prototyp nicht nachgewiesen.

Auch eine selektivere Bindung an Teilzustände wäre eine neue Vertragsversion. Vertrag 1 erlaubt keinen stillen Wechsel auf einen vermeintlich kompatiblen Zustand. Eine aufwendigere Variante darf deshalb nicht als bereits vorhandene Funktion des kleinen Prototyps verstanden werden.
