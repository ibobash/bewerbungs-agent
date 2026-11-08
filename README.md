# Bewerbungsagent

Der Agent verfolgt zwei getrennte Pfade: Anstellung und Selbstständigkeit als
Kfz-Prüfingenieur. Er ruft Stellen über vier öffentliche APIs ab, gleicht sie mit einem
Berufsprofil ab und erstellt einen Bericht mit direkten Anzeigenlinks,
Veröffentlichungsdatum, Bewertung und Begründung. Offizielle GTÜ-/KÜS-Programme
für Qualifizierung und Partnerschaften erscheinen getrennt von Stellenanzeigen.
Er verschickt keine Bewerbungen und nimmt keinen Kontakt zu Organisationen auf.
Python 3.10+ reicht aus; zusätzliche Pakete sind nicht erforderlich.

## Neue Suche direkt im Chat

In diesem Projektchat genügt die Nachricht **„Starte eine neue Suche“**.
Der Codex-Agent verwendet das gespeicherte private Profil, aktualisiert die
Quellen und liefert `reports/dashboard.html` mit einer sortier- und filterbaren
Liste, Eignungsskala und aufklappbarer Bewertungsbegründung. Dafür muss der
Benutzer weder Befehle eingeben noch GitHub öffnen. Der Ablauf für Codex ist in
`AGENTS.md` festgehalten. Es handelt sich um einen Auftrag im Chat, nicht um einen
ständig laufenden KI-Dienst oder eine öffentlich gehostete Webanwendung.

Die persönliche Suche begrenzt Anzeigen verbindlich auf die im Profil genannten
Orte im Großraum München/Westen. Nationale oder internationale Alternativen
werden nicht mehr ergänzt. Die Ortsliste bestätigt **keinen exakten 20-km-Radius**:
Ohne hinreichende Arbeitsplatzadresse erscheint ein Kandidat nur in der
regionalen Prüfliste. Das Dashboard nennt separat die Zahl tatsächlich im Radius
bestätigter Stellen. Aktuell wird keine exakte Distanzverifikation automatisiert.

Junior-/Trainee-/Einstiegsrollen werden ausgeschlossen. Rollen ohne erkennbaren
Nachweis geforderter Erfahrung werden standardmäßig ausgeblendet und lassen sich
als Prüffälle einblenden. Mindestens zwei Kompetenzgruppen müssen zum Profil
passen; ein Ingenieurtitel allein reicht nicht. Soweit bekannt, sind Anzeigen
höchstens 90 Tage alt. Homeoffice bleibt Pflicht im Anstellungspfad.

Fehlt ein persönliches Profil, stoppt ein normaler Lauf vor dem API-Abruf. Es
werden keine ungefilterten Testdaten als Ersatzbericht ausgegeben. Nur ein
expliziter PR-Techniktest darf ohne Profil laufen.

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
PR-Tests erhalten kein Profil-Secret, überspringen Remotive zur Schonung der API
und erstellen einen klar markierten,
unpersonalisierten technischen Bericht. Ohne Secret stoppen tägliche und manuelle
reguläre Läufe mit einer klaren Fehlermeldung.
Ungültige Profile führen zu einem sichtbaren Fehler, nicht zu einer stillen Ersatzsuche.

`profile.example.json` dokumentiert das Format, enthält aber absichtlich keine
persönlichen Angaben. Ein leeres `target_roles` ist ungültig:

- `target_roles`: Zielpositionen oder Titelvarianten, mindestens eine davon muss
  im Anzeigentitel vorkommen.
- `skills`: Nachweisbare Kenntnisse, die in der Anzeige gesucht werden.
- `locations`: Orts-/Länderbegriffe, mindestens einer muss im angegebenen Ort
  vorkommen; leer bedeutet keine Ortsbeschränkung. Kein geographischer Radius.
- `remote_only`: Nur als remote markierte Anzeigen, falls `true`.
- `homeoffice_required`: Nur Anzeigen mit positivem Homeoffice-/Hybrid-Hinweis
  im Text oder in Quellmetadaten. Negative Hinweise werden ausgeschlossen.
  Die Erkennung ist regelbasiert; die konkrete Vereinbarung muss geprüft werden.
- `preferred_roles` und `preferred_locations`: Vorrangige Titel und Ortsnamen.
  Bevorzugte Titel bestimmen die Sortierung. Die Ortsliste wird bei persönlichen
  Läufen als verbindliche regionale Vorauswahl verwendet, sofern `locations` leer
  ist; sie ist keine harte Entfernungsmessung.
- `salary_target_eur`: Jahresgehaltsziel als Hinweis; kein bestätigter Anzeigenlohn.
- `excluded_role_keywords`: Ausschluss unpassender Titel (z. B. IT-Infrastruktur
  oder Einstiegsprogramme), ohne jeden Nebensatz der Anzeige auszuschließen.
- `competency_groups`: Kompetenzgruppen mit `name` und Synonymen in `terms`;
  diese verhindern, dass viele ähnliche Stichwörter die Bewertung aufblasen.
- `experience_checks`: Nachweise mit `role_terms`, `documented_years` und
  `evidence`, um Gesamtberufserfahrung von Spezialerfahrung zu unterscheiden.
- `min_competency_groups`: Mindestzahl passender Gruppen (Standard 2).
- `experienced_only`: Einstiegsrollen ausfiltern (Standard true).
- `max_age_days`: Maximales Anzeigenalter, soweit Datum vorhanden (Standard 90).
- `self_employment`: Separates Profil für Prüfingenieur-Anzeigen. Homeoffice- und
  Gehaltsvorgaben des Anstellungspfads werden nicht automatisch übernommen.
- `required_keywords`: Alle Begriffe müssen in Titel/Beschreibung/Tags vorkommen.
- `required_any_keywords`: Mindestens ein Begriff muss vorkommen, sofern angegeben;
  geeignet, um technische Branchen von ähnlich benannten IT-Rollen zu unterscheiden.
- `exclude_keywords`: Anzeigen mit einem dieser Begriffe werden ausgeschlossen.
- `search_note`: Offene Wünsche oder Annahmen, die im Bericht sichtbar bleiben.

Das vorbereitete private Profil verwendet den hochgeladenen Lebenslauf und die
bestätigten Suchwünsche. Die frühere Python-/SQL-Testsuche wird nicht übernommen.
Münchner Westen/20 km bleiben das Suchziel; wegen fehlender genauer
Arbeitgeberadressen wird kein Treffer als nachweislich innerhalb von 20 km
ausgegeben. Überregionale Anzeigen werden ausgeschlossen. Voll-/Teilzeit,
Gehaltsniveau und genaue Entfernung werden noch nicht strukturiert geprüft.

## Quellen und Grenzen

- **Arbeitnow**: https://www.arbeitnow.com/api/job-board-api — standardmäßig bis
  zu zehn Seiten (höchstens etwa 3.000 Anzeigen), mit Original-Anzeigenlinks.
- **Remotive**: https://remotive.com/api/remote-jobs — öffentliche Remote-Stellen,
  mit Quellenangabe und Rücklink zu Remotive; API-Anzeigen sind 24 Stunden verzögert.
  Empfehlung des Anbieters: höchstens vier Abrufe pro Tag. Deshalb technische
  Testläufe und manuelle Starts sparsam einsetzen. Keine Weiterverteilung an
  Stellenaggregatoren, keine Registrierungsschranke.
- **Remote OK**: https://remoteok.com/api — mit Quellenangabe und Rücklink
  zu Remote OK; ohne Verwendung des Logos.
- **Brainlab / SmartRecruiters**: öffentliche Arbeitgeber-API, deutsche technische
  Rollen einschließlich vollständiger Anzeigentexte, Direktlinks zur offiziellen
  Stellenanzeige. Erweitert die Suche gezielt um Medizintechnik.
- **GTÜ und KÜS**: drei offizielle Informationsseiten zu Qualifizierung und
  Selbstständigkeit. Erreichbarkeit und passender Inhalt werden täglich geprüft.
  Sie sind keine konkreten Stellenanzeigen und bestätigen keine lokale
  Partnerschaft, Vergütung oder persönliche Zulassung. Fehlende
  Veröffentlichungsdaten werden als unbekannt ausgegeben.

Die Quellen sind keine vollständige Abdeckung des deutschen Stellenmarkts,
insbesondere nicht sämtlicher Automotive-/Ingenieurstellen. Es werden keine
Login-Bereiche oder gesperrten Webseiten ausgelesen. Die Quellen liefern Daten
auch außerhalb Deutschlands. Fehlende oder ungültige Veröffentlichungsdaten
bleiben **Nicht angegeben**. Aktualität und fortbestehende Verfügbarkeit müssen
anhand des Anzeigenlinks geprüft werden.

Der Score ist ein erklärbarer **Profilabgleich**, keine bestätigte Eignung:
Zielrolle bis 25 Punkte, nachgewiesenes Erfahrungsniveau bis 20, Kompetenzgruppen
bis 25, Zielbranche bis 10, Homeoffice bis 10 und Arbeitsort bis 10 Punkte. Ein
passender Ortsname allein erhält nur 5 Ortspunkte. Ab 80 Punkten ist der Abgleich
stark, ab 70 gut und ab 55 teilweise passend. Die Gesamtberufserfahrung wird nicht
automatisch als Nachweis einer geforderten Spezialerfahrung gewertet, wenn
`experience_checks` entsprechende CV-Nachweise hinterlegt. Die Skala ist
regelbasiert und keine Zusage oder Bewerbungs-Erfolgswahrscheinlichkeit. Nicht genannte Kenntnisse sind
kein Beleg für fehlende Qualifikation. Berufserfahrung, fachliche Tiefe, Arbeitszeit,
Sprache, Gehalt und Länderberechtigung bei Remote-Arbeit bedürfen einer Prüfung.
Der Bericht zeigt standardmäßig höchstens 50 Ergebnisse je Pfad und nennt auch
die Gesamtzahl. Qualifizierungs-/Partnerprogramme erhalten keinen Eignungsscore.
Für den Prüfingenieur-Pfad sind insbesondere die Voraussetzungen der
[Anlage VIIIb StVZO](https://www.gesetze-im-internet.de/stvzo_2012/anlage_viiib.html)
mit der Überwachungsorganisation zu klären. Ingenieurabschluss und bestehende
nebenberufliche Gutachtertätigkeit allein bestätigen keine Prüfingenieur-Betrauung.
Gleiche Titel/Firmen/Orte werden zusammengeführt; unterschiedliche Ortsangaben
können dazu führen, dass dieselbe Stelle mehrfach erscheint.

Öffentliche Quelldaten werden pro UTC-Tag lokal und in GitHub Actions
zwischengespeichert, um unnötige Wiederholungsabrufe zu vermeiden. Der Cache
enthält keine Berufsprofile. PR-Tests lassen Remotive aus; tägliche und manuelle
reguläre Läufe verwenden alle vier APIs.

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

Ergebnisse: `reports/dashboard.html` (auch als `report.html`), `reports/report.md`
und `reports/results.json`. Ohne `--profile` stoppt der normale Tageslauf.
`python -m bewerbungs_agent.daily --diagnostic` ist ein ausdrücklicher Techniktest.
Für den Agenten: `python -m bewerbungs_agent.search --refresh` findet das lokale
Privatprofil selbst. Der Parameter aktualisiert die Quellen; Remotive wird bei
mehrfachen Suchen am selben UTC-Tag aus dem Tagescache geladen.
Die frühere Test-CLI `python -m bewerbungs_agent --keywords ...` bleibt verfügbar;
sie wird für die tägliche profilbasierte Suche nicht verwendet.

## Verbindungsprüfung

Am 4. November 2026 waren GitHub sowie alle vier eingebundenen Stellen-APIs per
HTTPS erreichbar. Der öffentliche GitHub-Lesezugriff liefert HTTP 200.
Der zusätzlich getestete Bundesagentur-Endpunkt
`https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs?was=Python&size=3`
lieferte HTTP 403 mit und ohne `X-API-Key: jobboerse-jobsuche`, ohne erläuternden
Fehlertext. Deshalb wird er nicht als funktionierende Datenquelle angeboten.
Das belegt keinen bestimmten fehlenden Schlüssel. Für seine Einbindung müssen
zunächst die aktuellen Zugangsvoraussetzungen des Anbieters geklärt werden.

## Lebenslauf auf ATS-Lesbarkeit prüfen

Im Chat genügt „Prüfe meinen Lebenslauf“ mit dem aktuellen Upload. Der Agent
verwendet den lokalen Checker und erläutert konkrete Verbesserungen. Mit einer
Zielanzeige kann er zusätzlich relevante Anforderungen abgleichen.

```bash
python -m bewerbungs_agent.ats /privat/Lebenslauf.pdf --output /privat/ats.json
python -m bewerbungs_agent.ats /privat/Lebenslauf.docx --keywords "Requirements Engineering" "IBM DOORS"
```

PDF benötigt das lokale Programm `pdftotext` (Poppler). TXT, Markdown, DOCX und
PPTX funktionieren mit der Python-Standardbibliothek. PPTX wird als Ausgangsdatei
unterstützt; für Bewerbungsportale gelten deren Formatvorgaben. Der Bericht zeigt
Textauszug, Hinweise zu Abschnitten, Kontakt, Zeiträumen, Tabellen und einen
optionalen Wortabgleich. Bild-PDFs benötigen vorher OCR. Eine visuelle Kontrolle,
semantische Eignungsbewertung und ein Test in einem echten ATS sind nicht enthalten.
Kein universeller ATS-Score wird berechnet. Nicht gefundene Begriffe belegen keine
fehlende Qualifikation; nur tatsächlich vorhandene Kenntnisse ergänzen.

**Privat halten:** JSON-Berichte enthalten den vollständigen ausgelesenen
Lebenslauf. Außerhalb des öffentlichen Repositorys speichern, nicht committen
und nicht in Actions-Berichte übernehmen. Der Checker sendet keine Daten an APIs.
