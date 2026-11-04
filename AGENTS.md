# Bewerbungsagent: Arbeit mit dem Benutzer

Der Benutzer möchte Suchläufe im Chat beauftragen, ohne GitHub-Schritte oder
Programmierbefehle selbst auszuführen. Bei „Starte eine neue Suche“ oder einer
sinngleichen Bitte:

1. Den aktuellen privaten Profilstand verwenden. Der Suchbefehl findet ihn über
   `--profile`, `JOB_PROFILE_PATH`, `/workspace/private-job-profile.json` oder
   `profile.json`. Kein Ersatzprofil erfinden und keine Python-/SQL-Testkriterien
   übernehmen. Änderungen des Benutzers in das private Profil übernehmen.
2. Aus dem Repository `python -m bewerbungs_agent.search --refresh` ausführen.
   Dieser Befehl aktualisiert die Quellen und schreibt ein interaktives Dashboard
   nach `reports/dashboard.html`. Remotive wird wegen der API-Empfehlung höchstens
   einmal pro UTC-Tag abgerufen; weitere Quellen dürfen aktualisiert werden.
   Beim Entwickeln `--skip-remotive` nutzen, um die API nicht unnötig zu belasten.
3. `reports/results.json` lesen. Die besten konkreten Anzeigen mit dem tatsächlichen
   CV und den Benutzerwünschen prüfen. Weder allgemeine Berufserfahrung als
   Nachweis jeder geforderten Spezialerfahrung behandeln noch eine Ortsangabe als
   belegte Entfernung. Keine Resultate hinzufügen, um eine leere Liste zu füllen.
4. Dem Benutzer den Dashboard-Link und knapp die Trefferzahl, die beste Passung
   sowie wichtige offene Punkte nennen. Quellenfehler und zwischengespeicherte
   Daten bei Bedarf kenntlich machen. Die automatische Skala ist ein erklärbarer
   Profilabgleich und keine Erfolgswahrscheinlichkeit oder externe KI-API.
5. GitHub ist für einen Suchlauf in diesem Chat nicht erforderlich. Für Änderungen
   am Programm gilt der PR-Workflow. Ein Chat-Auftrag startet keine dauerhafte
   Hintergrund-KI außerhalb dieses Chats; dafür existiert die separate tägliche
   GitHub-Actions-Ausführung.

Lebenslauf und tatsächliches Profil nicht in dieses öffentliche Repository
committen. Keine Bewerbungen versenden und keine Organisation kontaktieren, ohne
entsprechenden Auftrag. Die beiden Pfade Anstellung und Prüfingenieur-
Selbstständigkeit getrennt halten; Gehalt/Homeoffice des Angestelltenpfads nicht
auf Qualifizierungs- und Partnerprogramme übertragen.
