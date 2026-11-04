# Bewerbungsagent

Der Agent ruft Stellen über drei öffentliche APIs ab, gleicht sie mit einem
Berufsprofil ab und erstellt einen Bericht mit direkten Anzeigenlinks,
Veröffentlichungsdatum, Bewertung und Begründung. Er verschickt keine Bewerbungen.
Python 3.10+ reicht aus; zusätzliche Pakete sind nicht erforderlich.

## Täglichen Bericht auf GitHub ansehen

1. Im Repository auf **Actions** und **Tägliche Stellensuche** klicken.
2. Den neuesten ausgeführten Lauf öffnen. Der Bericht steht direkt auf dessen
   Übersichtsseite unter der Zusammenfassung. Ein übersprungener Zeitprüflauf
   enthält keinen Bericht; dann den vorherigen ausgeführten Lauf öffnen.
3. Alternativ unter **Artifacts** die Datei **stellenbericht-…** herunterladen,
   entpacken und **report.html** öffnen. Der Download enthält auch Markdown und JSON.

GitHub führt die Suche auf seinen Servern aus. Der eigene Computer darf aus sein.
Geplant ist täglich ungefähr **07:00 Uhr Europe/Berlin**, auch bei Sommerzeit.
GitHub kann geplante Läufe verzögern. Die Planung wird erst aktiv, wenn die
Workflow-Datei auf dem Standardbranch `main` liegt. Öffentliche Repositories
können geplante Workflows nach 60 Tagen ohne Repository-Aktivität deaktivieren;
diese lassen sich auf der Actions-Seite wieder aktivieren. Ein zweiter UTC-Termin
wird wegen der Sommerzeit geprüft und außerhalb 07 Uhr übersprungen.
Manuell geht es über **Run workflow** auf der Actions-Seite.

Die Berichte bleiben als Artefakte 30 Tage verfügbar. Es gibt keine automatische
E-Mail-Zustellung. Bei einem öffentlichen Repository sind auch Actions-Berichte
öffentlich: Sie enthalten Stellen und passende Kompetenzstichwörter, keinen
Lebenslauf und keine Kontaktinformationen. Wer private Berichte braucht, sollte
GitHub-Berichte in einem privaten Repository ausführen.

## Privates Suchprofil einmalig hinterlegen

Das echte Profil wird **nicht ins öffentliche Repository eingecheckt**. Unter
**Settings → Secrets and variables → Actions → New repository secret** ein Secret
namens **JOB_PROFILE_JSON** anlegen und das vorbereitete Profil-JSON hineinkopieren.
Danach **Actions → Tägliche Stellensuche → Run workflow** starten. Das Profil
wird nur vorübergehend in einer geschützten Runner-Datei gespeichert und gelöscht.
PR-Tests erhalten kein Profil-Secret und erstellen einen klar markierten,
unpersonalisierten technischen Bericht. Ohne Secret gilt das auch für tägliche Läufe.
Ungültige Profile führen zu einem sichtbaren Fehler, nicht zu einer stillen Ersatzsuche.

`profile.example.json` dokumentiert das Format, enthält aber absichtlich keine
persönlichen Angaben. Ein leeres `target_roles` ist ungültig:

- `target_roles`: Zielpositionen oder Titelvarianten, mindestens eine davon muss
  im Anzeigentitel vorkommen.
- `skills`: Nachweisbare Kenntnisse, die in der Anzeige gesucht werden.
- `locations`: Orts-/Länderbegriffe, mindestens einer muss im angegebenen Ort
  vorkommen; leer bedeutet keine Ortsbeschränkung. Kein geographischer Radius.
- `remote_only`: Nur als remote markierte Anzeigen, falls `true`.
- `required_keywords`: Alle Begriffe müssen in Titel/Beschreibung/Tags vorkommen.
- `required_any_keywords`: Mindestens ein Begriff muss vorkommen, sofern angegeben;
  geeignet, um technische Branchen von ähnlich benannten IT-Rollen zu unterscheiden.
- `exclude_keywords`: Anzeigen mit einem dieser Begriffe werden ausgeschlossen.
- `search_note`: Offene Wünsche oder Annahmen, die im Bericht sichtbar bleiben.

Die aus einem Lebenslauf abgeleiteten Suchrichtungen sind vorläufig, bis
Zielpositionen und Suchwünsche bestätigt sind. Wohnort bedeutet nicht automatisch
gewünschter Arbeitsort. Ohne bestätigte Ortsvorgabe wird deshalb breit gesucht.
Voll-/Teilzeit, Gehalt und Pendelradius werden noch nicht strukturiert geprüft.

## Quellen und Grenzen

- **Arbeitnow**: https://www.arbeitnow.com/api/job-board-api — standardmäßig bis
  zu drei Seiten (etwa 900 Anzeigen), mit Original-Anzeigenlinks.
- **Remotive**: https://remotive.com/api/remote-jobs — öffentliche Remote-Stellen,
  mit Quellenangabe und Rücklink zu Remotive; API-Anzeigen sind 24 Stunden verzögert.
  Empfehlung des Anbieters: höchstens vier Abrufe pro Tag. Deshalb technische
  Testläufe und manuelle Starts sparsam einsetzen. Keine Weiterverteilung an
  Stellenaggregatoren, keine Registrierungsschranke.
- **Remote OK**: https://remoteok.com/api — mit Quellenangabe und Rücklink
  zu Remote OK; ohne Verwendung des Logos.

Die Quellen sind keine vollständige Abdeckung des deutschen Stellenmarkts,
insbesondere nicht sämtlicher Automotive-/Ingenieurstellen. Es werden keine
Login-Bereiche oder gesperrten Webseiten ausgelesen. Die Quellen liefern Daten
auch außerhalb Deutschlands. Fehlende oder ungültige Veröffentlichungsdaten
bleiben **Nicht angegeben**. Aktualität und fortbestehende Verfügbarkeit müssen
anhand des Anzeigenlinks geprüft werden.

Der Score ist ein erklärbarer **Textabgleich**, keine bestätigte Eignung:
60 Punkte für einen passenden Zielrollentitel und bis zu 40 Punkte für den Anteil
der im Anzeigentext genannten Profilkenntnisse. Nicht genannte Kenntnisse sind
kein Beleg für fehlende Qualifikation. Berufserfahrung, fachliche Tiefe, Arbeitszeit,
Sprache, Gehalt und Länderberechtigung bei Remote-Arbeit bedürfen einer Prüfung.
Der Bericht zeigt standardmäßig höchstens 50 Treffer und nennt auch die Gesamtzahl.
Gleiche Titel/Firmen/Orte werden zusammengeführt; unterschiedliche Ortsangaben
können dazu führen, dass dieselbe Stelle mehrfach erscheint.

Fällt eine Quelle aus, bleibt der Bericht aus den übrigen Quellen verfügbar und
nennt den Ausfall ausdrücklich. Liefern alle Quellen keine Anzeigen oder schlagen
alle fehl, schlägt der Lauf fehl. Auch bei Fehlern werden vorhandene Berichte
hochgeladen. Die Datenquellen können ihren Zugang jederzeit ändern.

## Lokal starten und testen

```bash
python -m bewerbungs_agent.daily --profile /pfad/zum/privaten-profil.json
python -m bewerbungs_agent.daily --profile /pfad/zum/privaten-profil.json --pages 5 --limit 100
python -m unittest discover -s tests -v
```

Ergebnisse: `reports/report.html`, `reports/report.md`, `reports/results.json`.
Ohne `--profile` wird nur ein markierter technischer Bericht erstellt.
Die frühere Test-CLI `python -m bewerbungs_agent --keywords ...` bleibt verfügbar;
sie wird für die tägliche profilbasierte Suche nicht verwendet.

## Verbindungsprüfung

Am 4. November 2026 waren GitHub sowie alle drei eingebundenen Stellen-APIs per
HTTPS erreichbar. Der öffentliche GitHub-Lesezugriff liefert HTTP 200.
Der zusätzlich getestete Bundesagentur-Endpunkt
`https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs?was=Python&size=3`
lieferte HTTP 403 mit und ohne `X-API-Key: jobboerse-jobsuche`, ohne erläuternden
Fehlertext. Deshalb wird er nicht als funktionierende Datenquelle angeboten.
Das belegt keinen bestimmten fehlenden Schlüssel. Für seine Einbindung müssen
zunächst die aktuellen Zugangsvoraussetzungen des Anbieters geklärt werden.
