# Document Consistency Review — Rollout Readiness

Stand: 8. Oktober 2026  
Entscheidung: `dcr-rollout-0002`  
Readiness: **`limited_pilot_ready`**  
Produktiver Rollout: **`pending`**

## Management-Zusammenfassung

Der Document Consistency Review ist technisch bereit für weitere, jeweils
separat genehmigte report-only Piloten. Der vollständige Pfad von manifestierten
Quellen über Providerprojektion, Normalisierung, deterministische Belegprüfung,
verblindete Katalogauswertung und menschliche Bewertung wurde erfolgreich
demonstriert.

Die Freigabe gilt nicht für automatischen Betrieb, blockierendes Enforcement,
Viewer-Veröffentlichung oder produktiven Rollout. Dafür fehlen insbesondere
eine wiederverwendbare Provider- und Aufbewahrungsentscheidung, ein bestätigter
produktiver Quellenscope, breitere Ground Truth, strukturierte Aufwand- und
Kostenmessung sowie eine getrennte Implementierungsabdeckung.

## Entscheidungsprofil

| Dimension | Entscheidung |
| --- | --- |
| Weitere Piloten | zulässig nach separater Genehmigung jedes Laufs |
| Betriebsart | ausschließlich report-only |
| Provider/Modell | pro Lauf ausdrücklich zu binden |
| Daten und Aufbewahrung | pro Lauf ausdrücklich zu bestätigen |
| Automatische oder geplante Ausführung | nicht autorisiert |
| Blocking | nicht autorisiert |
| Viewer-Veröffentlichung | nicht autorisiert |
| Produktiver Rollout | `pending` |

## Kriterienbewertung

| Kriterium | Status | Begründung |
| --- | --- | --- |
| Provider und Modell | `partial` | Für einen Einmallauf exakt gebunden; keine wiederverwendbare Freigabe. |
| Datenfluss und Aufbewahrung | `partial` | Einmallauf akzeptiert und Rohantwort gelöscht; ZDR und Dauerprofil offen. |
| Begrenzter realer semantischer Pilot | `met` | Zwei registrierte requirements-only Quellen Ende zu Ende validiert. |
| Verblindeter synthetischer Katalog | `met` | 3/3 Fälle bestanden; Sollantworten nicht an den Provider übertragen. |
| Menschliche Finding-Bewertung | `met` | `DCR-SEM-001` als `helpful` klassifiziert. |
| Bekannte Misses und False Positives | `partial` | Nur drei synthetische Fälle, keine allgemeine Qualitätsrate. |
| Triageaufwand und Kosten | `partial` | Ablauf durchgeführt; strukturierte Zeit- und Kostendaten fehlen. |
| Produktiver Quellenscope | `open` | Zielpopulation noch nicht vollständig registriert und autorisiert. |
| Implementierungsabdeckung | `open` | Im semantischen Pilot nicht bewertet. |
| Veröffentlichung und Automatisierung | `open` | Weder verdrahtet noch autorisiert. |

## Nachweisbasis

- Der zweite begrenzte reale Pilot lieferte erstmals einen schema-validen,
  vollständig validierten Providerpfad; er enthielt keine Finding-Kandidaten.
- Der verblindete synthetische Lauf lieferte einen belegbaren Konfliktkandidaten
  und bestand alle drei Katalogfälle.
- Beide exakten Finding-Belege waren gültig; keine Quarantäne entstand.
- Die Prompt-Injection-Fixture wurde nicht befolgt.
- Die menschliche Bewertung bestätigte den Kandidaten als hilfreich und hielt
  die normative Lösung ausdrücklich offen.
- Alle Nachweise in `rollout-decision-v2.json` sind per SHA-256 gebunden.

## Bedingungen für einen weiteren begrenzten Pilotlauf

Vor jedem Lauf müssen mindestens feststehen:

1. exakter Quellenumfang und Manifest;
2. Provider und angezeigte Modellkennung;
3. zulässiger Datenfluss und ausgeschlossene Inhalte;
4. Provider- und lokale Aufbewahrung;
5. Rohantwortbehandlung;
6. report-only Betriebsart;
7. menschlicher Reviewer und Entscheidungsgrenze;
8. Kosten- und Größenlimit;
9. Verhalten bei Provider-, Schema- oder Kontextfehlern.

Jeder Lauf erhält einen eigenen Review- und Evidenzdatensatz. Eine frühere
Einmalfreigabe darf nicht wiederverwendet werden.

## Weg zur Produktionsreife

1. Produktiven Dokumentenscope registrieren, klassifizieren und autorisieren.
2. Reale Ground Truth mit fachlichen Ownern aufbauen.
3. Positive, negative, unklare und nicht beurteilbare Fälle erweitern.
4. Mindestens einen providerneutralen Methodikvergleich durchführen.
5. Laufzeit, Modellkosten und menschlichen Triageaufwand strukturiert messen.
6. Dokumentenkonsistenz und Implementierungsabdeckung getrennt bewerten.
7. Wiederverwendbares Provider-, Datenschutz- und Aufbewahrungsprofil
   genehmigen.
8. Viewer-, Scheduling- und Blocking-Entscheidungen separat vorlegen.

## Entscheidungsgrenze

`limited_pilot_ready` ist eine technische Betriebsbereitschaft für kontrollierte
Einzelläufe. Der Status bestätigt weder allgemeine Modellqualität noch
Dokumentenkonsistenz, Compliance, Quellenautorität, Implementierungsabdeckung
oder Produktionsfreigabe.

