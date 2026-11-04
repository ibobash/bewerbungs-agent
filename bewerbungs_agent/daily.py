"""Daily multi-source search; no third-party dependencies."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .__main__ import fetch_jobs, plain_text


def request_json(url):
    with urlopen(Request(url, headers={"User-Agent": "bewerbungs-agent/0.2", "Accept": "application/json"}), timeout=40) as response:
        return json.load(response)


def publication(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).date().isoformat()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def normalize(raw, source):
    if source == "Arbeitnow":
        title, company, location = raw["title"], raw["company_name"], raw.get("location", "")
        remote, date, url = raw.get("remote", False), raw.get("created_at"), raw["url"]
    elif source == "Remotive":
        title, company, location = raw["title"], raw["company_name"], raw.get("candidate_required_location", "")
        remote, date, url = True, raw.get("publication_date"), raw["url"]
    else:
        title, company, location = raw["position"], raw["company"], raw.get("location", "")
        remote, date, url = True, raw.get("date", raw.get("epoch")), raw["url"]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Ungültiger Anzeigenlink")
    return dict(title=title, company=company, location=location or "Nicht angegeben",
                remote=bool(remote), published=publication(date), url=url, source=source,
                description=plain_text(raw.get("description", "")), tags=raw.get("tags", []))


def collect(pages=3):
    jobs, statuses = [], []
    loaders = {
        "Arbeitnow": lambda: fetch_jobs(pages),
        "Remotive": lambda: request_json("https://remotive.com/api/remote-jobs")["jobs"],
        "Remote OK": lambda: [row for row in request_json("https://remoteok.com/api") if "position" in row],
    }
    for source, loader in loaders.items():
        try:
            raw_jobs = loader()
            normalized, invalid = [], 0
            for raw in raw_jobs:
                try:
                    normalized.append(normalize(raw, source))
                except (KeyError, ValueError, TypeError):
                    invalid += 1
            if raw_jobs and not normalized:
                raise ValueError("Keine gültigen Anzeigen im API-Ergebnis")
            jobs.extend(normalized)
            statuses.append(dict(source=source, ok=True, count=len(normalized), invalid=invalid))
        except Exception as error:
            # One source must not hide results from healthy sources.
            statuses.append(dict(source=source, ok=False, count=0,
                                 error=f"{type(error).__name__}: {error}"))
    seen, unique = set(), []
    for job in jobs:
        key = tuple(re.sub(r"\s+", " ", job[field]).strip().casefold() for field in ("company", "title", "location"))
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique, statuses


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("Das Profil muss ein JSON-Objekt sein.")
    for field in ("target_roles", "skills", "locations", "exclude_keywords", "required_keywords", "required_any_keywords"):
        value = profile.get(field, [])
        if not isinstance(value, list) or any(not isinstance(term, str) or not term.strip() for term in value):
            raise ValueError(f"{field} muss eine Liste nichtleerer Texte sein.")
    if not profile.get("target_roles"):
        raise ValueError("Mindestens eine tatsächliche Zielposition in target_roles ist erforderlich.")
    if not isinstance(profile.get("remote_only", False), bool):
        raise ValueError("remote_only muss true oder false sein.")
    if not isinstance(profile.get("search_note", ""), str):
        raise ValueError("search_note muss Text sein.")
    return profile


def contains(term, text):
    return re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", text.casefold()) is not None


def rank(jobs, profile):
    if profile is None:
        return [dict(job, score=None, reasons=["Berufsprofil fehlt; Eignung nicht bewertet."]) for job in jobs]
    validate_profile(profile)
    result = []
    for job in jobs:
        text = " ".join((job["title"], job["description"], " ".join(job["tags"])))
        roles = [term for term in profile["target_roles"] if contains(term, job["title"])]
        if not roles:
            continue
        if any(contains(term, text) for term in profile.get("exclude_keywords", [])):
            continue
        if not all(contains(term, text) for term in profile.get("required_keywords", [])):
            continue
        if profile.get("required_any_keywords") and not any(contains(term, text) for term in profile["required_any_keywords"]):
            continue
        if profile.get("remote_only") and not job["remote"]:
            continue
        if profile.get("locations") and not any(contains(term, job["location"]) for term in profile["locations"]):
            continue
        skills = [term for term in profile.get("skills", []) if contains(term, text)]
        total = len(profile.get("skills", []))
        score = round(60 + 40 * len(skills) / total) if total else 60
        reasons = ["Zielposition im Titel: " + ", ".join(roles),
                   "Genannte Kenntnisse: " + (", ".join(skills) or "keine aus dem Profil")]
        result.append(dict(job, score=score, reasons=reasons))
    return sorted(result, key=lambda j: (j["score"] or 0, j["published"] or ""), reverse=True)


def markdown_text(value):
    return escape(str(value)).replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;").replace("\n", " ")


def write_report(directory, jobs, statuses, personalized, total, limit=50, search_note=""):
    directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds")
    shown = jobs[:limit]
    mode = "Profilbasierte Suche" if personalized else "TECHNISCHER TEST – Berufsprofil fehlt, keine Eignungsbewertung"
    data = dict(generated_at=now, mode=mode, personalized=personalized, search_note=search_note,
                fetched=total, matched=len(jobs), displayed=len(shown), sources=statuses, jobs=shown)
    (directory / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Täglicher Stellenbericht", "", mode, "", f"Erstellt: {now}", "",
             f"{total} eindeutige Anzeigen abgerufen · {len(jobs)} Treffer · {len(shown)} angezeigt.", "",
             "## Quellenstatus", ""]
    for status in statuses:
        lines.append(f"- {status['source']}: " + (f"{status['count']} Anzeigen; {status['invalid']} ungültige übersprungen" if status['ok'] else "FEHLER: " + markdown_text(status['error'])))
    lines += ["", "Bewertung: Textabgleich, keine bestätigte berufliche Eignung. Zielposition im Titel: 60 Punkte; "
              "Anteil genannter Profilkenntnisse: bis zu 40 weitere Punkte. Fehlende Kenntnisse, Berufserfahrung, "
              "Gehalt, Arbeitszeit und tatsächliche Einstellungsberechtigung müssen geprüft werden. "
              "Remote bedeutet nicht automatisch, dass Arbeit aus Deutschland erlaubt ist. "
              "Veröffentlichungsdaten stammen von der Quelle; unbekannte Daten werden nicht geschätzt. "
              "Remotive veröffentlicht seine API-Daten mit 24 Stunden Verzögerung.", ""]
    if search_note:
        lines += [markdown_text(search_note), ""]
    cards = []
    for job in shown:
        rating = f"{job['score']}/100 (Textabgleich)" if job['score'] is not None else "Nicht bewertet – Profil fehlt"
        date = job['published'] or "Nicht angegeben"
        url = job['url'].replace("(", "%28").replace(")", "%29").replace(" ", "%20").replace("<", "%3C").replace(">", "%3E")
        lines += [f"## {markdown_text(job['title'])}", "",
                  f"**{markdown_text(job['company'])}** · {markdown_text(job['location'])}", "",
                  f"Veröffentlicht: {date} · Remote: {'Ja' if job['remote'] else 'Nein'} · Bewertung: {rating}", "",
                  markdown_text("; ".join(job['reasons'])), "",
                  f"[Anzeige bei {job['source']} öffnen](<{url}>)", ""]
        cards.append(f"<article><h2>{escape(job['title'])}</h2><p><b>{escape(job['company'])}</b> · {escape(job['location'])}</p>"
                     f"<p>Veröffentlicht: {date} · Remote: {'Ja' if job['remote'] else 'Nein'} · {rating}</p>"
                     f"<p>{escape('; '.join(job['reasons']))}</p><a href=\"{escape(job['url'], quote=True)}\">Anzeige bei {job['source']} öffnen</a></article>")
    if not shown:
        lines += ["Keine passenden Stellen in den abgerufenen Quellen. Dies ist keine Aussage über den gesamten Stellenmarkt.", ""]
    (directory / "report.md").write_text("\n".join(lines), encoding="utf-8")
    html = ('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Stellenbericht</title><style>body{font:17px system-ui;max-width:960px;margin:2rem auto;padding:1rem;background:#f5f7fa;color:#182130}'
            'article{background:white;padding:1.2rem;margin:1rem 0;border:1px solid #ccd5df;border-radius:10px}a{color:#064ba4}h2{font-size:1.2rem}</style>'
            f'<h1>Täglicher Stellenbericht</h1><p><b>{escape(mode)}</b></p><p>{escape(now)} · {len(jobs)} Treffer · {len(shown)} angezeigt</p>'
            f'<p>{escape(search_note)}</p>'
            '<details><summary>Quellen und Grenzen der Bewertung</summary><pre style="white-space:pre-wrap">' + escape('\n'.join(lines[8:16])) + '</pre></details>'
            + ''.join(cards) + ('<p>Keine Treffer.</p>' if not cards else '') + '</html>')
    (directory / "report.html").write_text(html, encoding="utf-8")
    return data


def main():
    parser = argparse.ArgumentParser(description="Tägliche Stellensuche über drei öffentliche APIs")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--pages", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit muss positiv sein")
    try:
        profile = validate_profile(json.loads(args.profile.read_text(encoding="utf-8"))) if args.profile else None
        jobs, statuses = collect(args.pages)
        results = rank(jobs, profile)
        data = write_report(args.report_dir, results, statuses, profile is not None, len(jobs), args.limit,
                            profile.get("search_note", "") if profile else "")
        print(f"{data['fetched']} Anzeigen, {data['matched']} Treffer. Bericht: {args.report_dir / 'report.html'}")
        for status in statuses:
            print(f"{status['source']}: {'OK' if status['ok'] else 'FEHLER'} ({status['count']})")
        return 0 if any(s["ok"] and s["count"] > 0 for s in statuses) else 1
    except (OSError, ValueError) as error:
        print(f"Konfigurationsfehler: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
