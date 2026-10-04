# 1 Technische Problemstellung

## 1.1 Gegenstand und technisches Gebiet

Gegenstand ist die computerimplementierte Bindung einer Freigabe an einen genau bestimmten Ausführungskontext. Das Verfahren richtet sich an Systeme, die eine Aktion vorbereiten, eine gesonderte Zustimmung einholen und die Aktion erst später ausführen. Zwischen diesen Schritten können sich Daten, Berechtigungen oder ausführende Software ändern. Die technische Aufgabe besteht darin, eine veraltete Freigabe vor einem geschützten Schreibvorgang zuverlässig zu erkennen und die tatsächlich ausgeführte Zustandsänderung nachprüfbar aufzuzeichnen.

Der vorliegende Funktionsprototyp gehört zum privaten Repository `joku-dev/devsecops-governance-framework`. Dieses verarbeitet technische Prüfergebnisse und daraus abgeleitete Governance-Zustände. Die hier untersuchte Lösung ist als eigener Forschungsbereich implementiert. Der nachgewiesene Effekt ist die Veröffentlichung eines lokalen Testartefakts in einem Transaktionsverzeichnis. Kapitel 3 beschreibt den ausführbaren Vertrag; Kapitel 5 ordnet jede wesentliche Funktion dem Quellcode und den Nachweisen zu.

## 1.2 Das konkrete technische Problem

Eine Zustimmung ist nur dann für eine spätere Aktion aussagekräftig, wenn klar ist, welche Eingaben, welche Vorgeschichte, welche aktuelle Zustandsableitung und welche Implementierung die zustimmende Stelle zugrunde gelegt hat. Eine Bestätigung allein des Aktionsnamens, eines Tickets oder eines früheren Berichts kann diesen Zusammenhang verlieren. Die gespeicherte Zustimmung kann unverändert bleiben, obwohl das System inzwischen eine andere technische Situation verarbeitet.

Ein Beispiel: Eine Person prüft einen Vorgang auf Grundlage des Prüflaufs E1 und der Auswertungssoftware I1. Während die Zustimmung eingeholt wird, geht Prüflauf E2 ein oder die Auswertungssoftware wird auf I2 geändert. Der spätere Ausführungsprozess findet weiterhin eine Zustimmung zum Vorgang. Ohne erneute Bindungsprüfung könnte er sie für einen Kontext verwenden, den die Person nicht geprüft hat. Auch zwei parallel gestartete Prozesse können dieselbe Freigabe verwenden und einen Effekt mehrfach erzeugen.

Die technische Problemformulierung lautet: Wie kann ein ausführendes System unmittelbar vor einer Zustandsänderung feststellen, dass der vollständige freigegebene Kontext weiterhin dem tatsächlichen Kontext entspricht, und die Prüfung mit dem beobachtbaren Schreibeffekt so verbinden, dass konkurrierende lokale Ausführungen keine zweite Publikation unter demselben alten Antrag erzeugen?

Diese Fehlerklasse ist mit Time-of-check/Time-of-use-Problemen verwandt: Ein geprüfter Zustand kann sich zwischen Prüfung und Nutzung ändern. Diese allgemeine Fehlerklasse ist bekannt und wird hier nicht als neue Erkenntnis beansprucht. [E1]

## 1.3 Drei unterschiedliche Arten von Kontext

**Historie:** Welche konkrete geordnete Folge akzeptierter Transaktionen liegt vor? Eine zusätzliche Auditnotiz verändert diese Folge auch dann, wenn sie die sachliche Bewertung nicht verändert.

**Semantischer Zustand:** Welche für die Aktion festgelegten Werte entstehen aus einer deterministischen Verarbeitung der Historie? Im Prototyp sind dies unter anderem die letzte Evidenz, die aktive Publikation, die Rollenbindung und das Profil. Der Begriff bezeichnet eine ausdrücklich definierte Datenprojektion; er umfasst nicht automatisch jede denkbare Bedeutung der Quelldaten.

**Implementierung:** Welche ausgewählten Dateien, Abhängigkeitsdeklarationen und Konfigurationsbytes bestimmen die geprüfte Ausführungslogik? Gleiche Eingangsdaten allein reichen nicht aus, wenn eine geänderte Auswertung oder Konfiguration einen anderen Effekt erzeugen kann.

Die technische Schwierigkeit besteht darin, diese drei Identitäten auseinanderzuhalten und zugleich gemeinsam an die konkrete Aktion zu binden. Ein Hash des gesamten historischen Datenbestands erlaubt beispielsweise keine getrennte Aussage darüber, ob zwei Historien denselben definierten Zustand erzeugen.

## 1.4 Fehlerszenarien und gewünschtes Verhalten

| Szenario | Technisch gewünschtes Verhalten |
|---|---|
| Nach der Zustimmung wird neue Evidenz akzeptiert | Alten Antrag zurückweisen |
| Nur die aufbewahrte Historie ändert sich | Nach dem strikten Vertrag ebenfalls zurückweisen |
| Ausführungsrelevante Datei oder Konfiguration ändert sich | Geänderte Implementierungsbindung erkennen |
| Aktionsinhalt wird nachträglich ausgetauscht | Fehlende Übereinstimmung mit der Erklärung erkennen |
| Rolle, Profil oder Providererklärung ändern sich | Vor einer neuen Publikation zurückweisen |
| Zwei Prozesse verwenden denselben Antrag | Höchstens eine Publikation im gemeinsamen lokalen Ledger |
| Eine Korrektur wird später erforderlich | Historische Daten erhalten und aktuelle Wirksamkeit gezielt ändern |

## 1.5 Vorhandene Schutzmechanismen und verbleibende Untersuchungsfrage

Das Ausgangsrepository besitzt bereits Request-Digests, Prüfungen auf erwartete Historien-Heads und Sequenzen, Providerprüfungen, Implementierungsmanifeste sowie einen atomaren lokalen Writer. Diese Eigenschaften sind ein relevanter Ausgangspunkt. Der Prototyp ersetzt sie nicht durch eine Behauptung, frühere Freigaben seien ungebunden gewesen.

Untersucht wird ihre ausdrückliche Zusammenführung mit getrennt typisierten History-, State- und Implementation-Commitments sowie ihrer erneuten Auswertung an derselben lokalen Publikationsgrenze. Ein zusätzliches History-Commitment kann gegenüber einer korrekt geprüften Head-Bindung redundant sein. Diese Redundanz wird durch einen Weglassversuch sichtbar. Die zu prüfende mögliche Besonderheit liegt daher in einer konkreten technischen Merkmalskombination und deren Ausgestaltung, nicht in der isolierten Verwendung eines Hashwerts.

## 1.6 Abgrenzung der Aufgabenstellung

Der Nachweis betrifft weder die fachliche Richtigkeit einer Freigabe noch die Wahrheit der Eingangsevidenz. Er attestiert keine geladene Maschineninstruktion und beweist keine körperliche Anwesenheit einer Person. Ebenso wenig demonstriert er bereits eine verteilte Transaktion mit einem Deployment-System oder einen Betrieb für 1.500 Repositories. Diese Grenzen bestimmen, welche technischen Aussagen sich aus den Versuchen ableiten lassen.
