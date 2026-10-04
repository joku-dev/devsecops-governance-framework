# Vertrauliche Unterlagen für die Patentberatung

Dieses Paket erläutert die zustandsgebundene Autorisierung anhand eines ausführbaren lokalen Funktionsprototyps. Es enthält die fünf angeforderten Themen und einen ergänzenden Fragenkatalog für die Beratung. Referenzstand ist `56ed0c743121fddc9d117b69eb470493dff5046d`, Dokumentfassung 1.0 vom 20. September 2026.

## Lesen und weitergeben

- **Hauptunterlage:** [Technische Unterlagen als PDF](Patentanwalt-Unterlagen-Zustandsgebundene-Autorisierung.pdf).
- **Komplettes Weitergabepaket:** [ZIP mit PDF, Texten, Quellcodeauszug und Nachweisen](Patentanwalt-Paket-Zustandsgebundene-Autorisierung.zip).
- **Paketidentität und Prüfprotokoll:** [PACKAGE.json](PACKAGE.json).

Das ZIP ist zur gezielten Weitergabe durch den Maintainer bestimmt. Es ist nicht verschlüsselt und wurde nicht an Dritte versendet. GitHub-Links benötigen Zugriff auf das private Repository; die beigefügten Dateien erlauben die Offline-Inspektion.

## Die fünf gewünschten Themen

1. [Technische Problemstellung](01-problemstellung.md)
2. [Lösungsansatz und technische Merkmale](02-loesungsansatz.md)
3. [Design und Architektur](03-design-und-architektur.md)
4. [Anwendungen in KI, Agentensystemen und weiteren Bereichen](04-anwendungsfelder.md)
5. [Implementierungsreferenzen und Nachweise](05-implementierungsreferenzen.md)

Ergänzend: [Herkunft und Fragen für die anwaltliche Prüfung](06-herkunft-und-prueffragen.md).

Die Markdown-Dateien sind die editierbare Textgrundlage des PDFs. Das PDF enthält außerdem die daraus erzeugte Leseführung und dieselben Architekturabbildungen. Die bestehenden Forschungsdokumente unter `experiments/state_binding/` bleiben die Detailreferenz des Prototyps; dieses Paket ist deren adressatengerechte Erläuterung.

## Inhalt des ZIP-Pakets

- `Patentanwalt-Unterlagen-Zustandsgebundene-Autorisierung.pdf`: zusammenhängende Hauptunterlage.
- `documents/`: die sechs editierbaren Kapitel und drei Diagramme als SVG.
- `source/`: gezielter, unveränderter Quellcodeauszug aus dem festen Referenzcommit sowie Prototyptests.
- `evidence/`: originale automatische und persönliche Nachweise, Prüfberichte und zugehörige Validierungsprotokolle.
- `SOURCE-MANIFEST.json`: Quellpfade und Dateihashes des Auszugs.
- `MANIFEST.json`: Dateihashes des gesamten Paketinhalts.
- `verify_package.py`: lesende Integritätsprüfung des ZIP-Pakets mit optionalem externem Digest.

Die Referenzimplementierung ist der eigene private Prototyp. Es werden keine weiteren Installationen derselben vollständigen Lösung bei Dritten behauptet. Die KI-Anwendungsformen sind nicht implementierte Übertragungsentwürfe. Herkunft, frühere Offenlegungen, Erfinderschaft und Patentfähigkeit müssen gesondert geprüft werden.

## Reproduzierbarer Dokumentbau

`build_packet.py` erzeugt PDF, SVG-Diagramme und das Weitergabepaket aus den Markdown-Kapiteln und dem festen Referenzcommit. Die Bildkontrolle erfolgt separat an gerenderten PDF-Seiten. Der Builder verändert weder die ursprünglichen Evidence-Pakete noch die gebundenen Implementierungsdateien. Aus dem Repository-Root:

```bash
python3 -m venv /tmp/counsel-document-build
/tmp/counsel-document-build/bin/python -m pip install -r \
  experiments/state_binding/counsel-package/requirements.txt
/tmp/counsel-document-build/bin/python \
  experiments/state_binding/counsel-package/build_packet.py
```

Die Build-Abhängigkeiten gehören ausschließlich zum Dokumentbau. Sie ändern die Validierungstoolchain des Governance-Repositorys nicht. Ein erneuter Build benötigt Git-Zugriff auf den lokal vorhandenen Referenzcommit; er fragt keinen Provider ab und führt keine persönliche Aktion aus.
