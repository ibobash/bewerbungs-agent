"""Daily multi-source search; no third-party dependencies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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


def fetch_brainlab():
    """Public employer postings; Germany-based technical roles with full details."""
    base = "https://api.smartrecruiters.com/v1/companies/Brainlab/postings"
    payload = request_json(base + "?limit=100")
    for offset in range(100, payload.get("totalFound", 0), 100):
        payload["content"].extend(request_json(base + f"?limit=100&offset={offset}")["content"])
    rows = [row for row in payload["content"]
            if row.get("location", {}).get("country") == "de"
            and re.search(r"engineer|entwick|system|projekt|project|verif|valid", row["name"], re.I)]

    def detail(row):
        # Construct the known provider URL rather than following API-supplied hosts.
        if not str(row["id"]).isdigit():
            raise ValueError("Ungültige Brainlab-Anzeigen-ID")
        result = request_json(base + "/" + str(row["id"]))
        if result.get("active") is False:
            return None
        return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        return [row for row in pool.map(detail, rows) if row is not None]


def home_office(text, remote=False, hybrid=False):
    """Require a positive indication; an onsite flag does not disprove hybrid text."""
    negative = r"(?:no|without|kein\w*|ohne)\s+(?:option\s+for\s+|Möglichkeit\s+(?:für|auf)\s+|Anspruch\s+auf\s+)?(?:remote|home\s*office|homeoffice|hybrid)|(?:remote|home\s*office|homeoffice|hybrid)\s+(?:work\s+)?(?:(?:is|ist)\s+)?(?:not|nicht)\s+(?:available|possible|möglich|vorgesehen)|fully\s+on[ -]?site|100\s*%\s*(?:on[ -]?site|vor\s+ort)"
    if re.search(negative, text, re.I):
        return False, "Widersprüchliche oder negative Homeoffice-Angabe; ausgeschlossen"
    positive = re.search(r"home[ -]?office|hybrid(?:es?|en?)?\s+(?:work(?:ing)?|model|arbeiten|arbeitsmodell|workplace)|mobiles?\s+arbeiten|mobile\s+working|work\s+from\s+home|remote\s+(?:work|working|option)", text, re.I)
    if positive:
        return True, f"Im Anzeigentext genannt: {positive.group(0)}"
    if remote or hybrid:
        return True, "Von der Quelle als remote/hybrid markiert"
    return False, "Homeoffice nicht belegt"


def normalize(raw, source):
    hybrid = False
    requirements_text = ""
    if source == "Arbeitnow":
        title, company, location = raw["title"], raw["company_name"], raw.get("location", "")
        remote, date, url = raw.get("remote", False), raw.get("created_at"), raw["url"]
    elif source == "Remotive":
        title, company, location = raw["title"], raw["company_name"], raw.get("candidate_required_location", "")
        remote, date, url = True, raw.get("publication_date"), raw["url"]
    elif source == "Remote OK":
        title, company, location = raw["position"], raw["company"], raw.get("location", "")
        remote, date, url = True, raw.get("date", raw.get("epoch")), raw["url"]
    elif source == "Brainlab (SmartRecruiters)":
        requirements_text = plain_text(raw.get("jobAd", {}).get("sections", {}).get("qualifications", {}).get("text", ""))
        title, company = raw["name"], raw["company"]["name"]
        location = raw.get("location", {}).get("fullLocation", "")
        remote = raw.get("location", {}).get("remote", False)
        hybrid = raw.get("location", {}).get("hybrid", False)
        date, url = raw.get("releasedDate"), raw["postingUrl"]
        raw = dict(raw, description=" ".join(section.get("text", "") for section in raw.get("jobAd", {}).get("sections", {}).values()),
                   tags=[raw.get("industry", {}).get("label", "")])
    else:
        raise ValueError("Unbekannte Stellenquelle")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Ungültiger Anzeigenlink")
    description = plain_text(raw.get("description", ""))
    homeoffice, evidence = home_office(description, bool(remote), bool(hybrid))
    return dict(title=title, company=company, location=location or "Nicht angegeben",
                remote=bool(remote), published=publication(date), url=url, source=source,
                description=description, tags=raw.get("tags", []),
                homeoffice=homeoffice, homeoffice_evidence=evidence, requirements_text=requirements_text)


def collect(pages=3, cache_dir=None, skip_remotive=False, refresh=False):
    jobs, statuses = [], []
    loaders = {
        "Arbeitnow": lambda: fetch_jobs(pages),
        "Remotive": lambda: request_json("https://remotive.com/api/remote-jobs")["jobs"],
        "Remote OK": lambda: [row for row in request_json("https://remoteok.com/api") if "position" in row],
        "Brainlab (SmartRecruiters)": fetch_brainlab,
    }
    for source, loader in loaders.items():
        if skip_remotive and source == "Remotive":
            statuses.append(dict(source=source, ok=False, skipped=True, count=0, error="Entwicklungstest: Abruf aus Rücksicht auf API-Limits übersprungen; bei täglichen Läufen aktiv."))
            continue
        try:
            cache = None
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
                key = re.sub(r"[^a-z]+", "-", source.casefold())
                source_pages = pages if source == "Arbeitnow" else 1
                cache = cache_dir / f"{datetime.now(timezone.utc).date()}-{key}-{source_pages}.json"
            cached = bool(cache and cache.exists() and (not refresh or source == "Remotive"))
            raw_jobs = json.loads(cache.read_text(encoding="utf-8")) if cached else loader()
            normalized, invalid = [], 0
            for raw in raw_jobs:
                try:
                    normalized.append(normalize(raw, source))
                except (KeyError, ValueError, TypeError):
                    invalid += 1
            if raw_jobs and not normalized:
                raise ValueError("Keine gültigen Anzeigen im API-Ergebnis")
            jobs.extend(normalized)
            if cache and not cached:
                cache.write_text(json.dumps(raw_jobs, ensure_ascii=False), encoding="utf-8")
            statuses.append(dict(source=source, ok=True, count=len(normalized), invalid=invalid, cached=cached))
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
    for field in ("target_roles", "skills", "locations", "exclude_keywords", "excluded_role_keywords", "required_keywords", "required_any_keywords", "preferred_roles", "preferred_locations", "excluded_locations"):
        value = profile.get(field, [])
        if not isinstance(value, list) or any(not isinstance(term, str) or not term.strip() for term in value):
            raise ValueError(f"{field} muss eine Liste nichtleerer Texte sein.")
    if not profile.get("target_roles"):
        raise ValueError("Mindestens eine tatsächliche Zielposition in target_roles ist erforderlich.")
    if not isinstance(profile.get("remote_only", False), bool):
        raise ValueError("remote_only muss true oder false sein.")
    if not isinstance(profile.get("search_note", ""), str):
        raise ValueError("search_note muss Text sein.")
    if not isinstance(profile.get("homeoffice_required", False), bool):
        raise ValueError("homeoffice_required muss true oder false sein.")
    for field in ("experienced_only", "focused_search"):
        if field in profile and not isinstance(profile[field], bool):
            raise ValueError(f"{field} muss true oder false sein.")
    if not isinstance(profile.get("max_age_days", 90), int) or not 1 <= profile.get("max_age_days", 90) <= 365:
        raise ValueError("max_age_days muss zwischen 1 und 365 liegen.")
    if not isinstance(profile.get("competency_groups", []), list):
        raise ValueError("competency_groups muss eine Liste sein.")
    if not isinstance(profile.get("min_competency_groups", 2), int) or profile.get("min_competency_groups", 2) < 0:
        raise ValueError("min_competency_groups muss eine nichtnegative ganze Zahl sein.")
    for group in profile.get("competency_groups", []):
        if not isinstance(group, dict) or not isinstance(group.get("name"), str) or not isinstance(group.get("terms"), list) or not group['terms'] or any(not isinstance(term, str) or not term.strip() for term in group['terms']):
            raise ValueError("Jede Kompetenzgruppe benötigt name und eine nichtleere terms-Liste.")
    if not isinstance(profile.get("experience_checks", []), list):
        raise ValueError("experience_checks muss eine Liste sein.")
    for check in profile.get("experience_checks", []):
        if not isinstance(check, dict) or not isinstance(check.get("role_terms"), list) or not check['role_terms'] or any(not isinstance(term, str) or not term.strip() for term in check['role_terms']) or not isinstance(check.get("documented_years"), (int, float)) or not isinstance(check.get("evidence"), str):
            raise ValueError("Ein Erfahrungsabgleich benötigt role_terms, documented_years und evidence.")
    salary = profile.get("salary_target_eur")
    if salary is not None and (isinstance(salary, bool) or not isinstance(salary, (int, float)) or salary <= 0):
        raise ValueError("salary_target_eur muss eine positive Zahl sein.")
    if profile.get("self_employment") is not None:
        if not isinstance(profile["self_employment"], dict) or "self_employment" in profile["self_employment"]:
            raise ValueError("self_employment muss ein einzelnes Suchprofil sein.")
        validate_profile(profile["self_employment"])
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
        if any(contains(term, job["title"]) for term in profile.get("excluded_role_keywords", [])):
            continue
        if any(contains(term, text) for term in profile.get("exclude_keywords", [])):
            continue
        if not all(contains(term, text) for term in profile.get("required_keywords", [])):
            continue
        if profile.get("required_any_keywords") and not any(contains(term, text) for term in profile["required_any_keywords"]):
            continue
        if profile.get("remote_only") and not job["remote"]:
            continue
        if profile.get("homeoffice_required") and not job.get("homeoffice", False):
            continue
        if profile.get("locations") and not any(contains(term, job["location"]) for term in profile["locations"]):
            continue
        skills = [term for term in profile.get("skills", []) if contains(term, text)]
        total = len(profile.get("skills", []))
        score = round(60 + 40 * len(skills) / total) if total else 60
        reasons = ["Zielposition im Titel: " + ", ".join(roles),
                   "Genannte Kenntnisse: " + (", ".join(skills) or "keine aus dem Profil")]
        preferred_role = any(contains(term, job["title"]) for term in profile.get("preferred_roles", []))
        nearby = any(contains(term, job["location"]) for term in profile.get("preferred_locations", []))
        reasons.append("Homeoffice: " + job.get("homeoffice_evidence", "Nicht geprüft"))
        if profile.get("preferred_locations"):
            reasons.append("Großraum München/westliche Nachbarorte genannt; Westlage und 20-km-Radius nicht verifiziert" if nearby
                           else "Außerhalb der erkannten Wunschregion oder Standort unklar; nur überregionale Alternative")
        if profile.get("salary_target_eur"):
            salary_text = f"{profile['salary_target_eur']:,.0f}".replace(",", ".")
            reasons.append(f"Gehaltsziel {salary_text} EUR/Jahr: nicht strukturiert verifiziert, mit Arbeitgeber klären")
        result.append(dict(job, score=score, reasons=reasons, preferred_role=preferred_role, preferred_location=nearby))
    return sorted(result, key=lambda j: (j["preferred_location"], j["preferred_role"], j["score"] or 0, j["published"] or ""), reverse=True)


def markdown_text(value):
    return escape(str(value)).replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;").replace("\n", " ")


def write_report(directory, jobs, statuses, personalized, total, limit=50, search_note=""):
    directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds")
    track_names = {"employment": "Pfad 1: Anstellung", "self_employment": "Pfad 2: Selbstständigkeit / Prüfingenieur"}
    shown = [job for track in track_names for job in
             [row for row in jobs if row.get("track", "employment") == track][:limit]]
    mode = "Profilbasierte Suche" if personalized else "TECHNISCHER TEST – Berufsprofil fehlt, keine Eignungsbewertung"
    data = dict(generated_at=now, mode=mode, personalized=personalized, search_note=search_note,
                fetched=total, matched=len(jobs), displayed=len(shown), sources=statuses, jobs=shown)
    (directory / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Täglicher Stellenbericht", "", mode, "", f"Erstellt: {now}", "",
             f"{total} eindeutige Einträge abgerufen · {len(jobs)} Ergebnisse einschließlich Programme · {len(shown)} angezeigt.", "",
             "## Quellenstatus", ""]
    for status in statuses:
        lines.append(f"- {status['source']}: " + (f"{status['count']} Einträge; {status['invalid']} ungültige übersprungen" if status['ok'] else ("ÜBERSPRUNGEN: " if status.get('skipped') else "FEHLER: ") + markdown_text(status['error'])))
    lines += ["", "Bewertung: erklärbarer Profilabgleich, keine bestätigte berufliche Eignung. Bei der fokussierten Anstellungssuche: "
              "Zielrolle 25, Erfahrung 20, Kompetenzgruppen 25, Branche 10, Homeoffice 10, Arbeitsort 10 Punkte. "
              "Ein passender Ortsname belegt noch keinen 20-km-Radius und erhält nur 5 Ortspunkte. "
              "80–100: starker, 70–79: guter, 55–69: teilweiser Profilabgleich; darunter geringe Übereinstimmung. "
              "Fehlende Kenntnisse, Berufserfahrung, "
              "Gehalt, Arbeitszeit und tatsächliche Einstellungsberechtigung müssen geprüft werden. "
              "Remote bedeutet nicht automatisch, dass Arbeit aus Deutschland erlaubt ist. "
              "Veröffentlichungsdaten stammen von der Quelle; unbekannte Daten werden nicht geschätzt. "
              "Remotive veröffentlicht seine API-Daten mit 24 Stunden Verzögerung.", ""]
    if search_note:
        lines += [markdown_text(search_note), ""]
    lines += ["Die Ergebnisse sind je Pfad getrennt. Qualifizierungs-/Partnerprogramme sind keine konkreten Stellenangebote. "
              "Für Prüfingenieure gelten insbesondere die Voraussetzungen der "
              "[Anlage VIIIb StVZO](https://www.gesetze-im-internet.de/stvzo_2012/anlage_viiib.html); "
              "ein Ingenieurabschluss oder eine nebenberufliche Gutachtertätigkeit allein bestätigt die Berechtigung nicht.", ""]
    previous_track = None
    for job in shown:
        track = job.get("track", "employment")
        if track != previous_track:
            lines += [f"# {track_names[track]}", ""]
            previous_track = track
        rating = f"{job['score']}/100 (Textabgleich)" if job['score'] is not None else "Nicht bewertet – Profil fehlt"
        if job.get("entry_type") == "programme":
            rating = "Qualifizierungs-/Partnerprogramm; individuelle Voraussetzungen offen"
        date = job['published'] or "Nicht angegeben"
        url = job['url'].replace("(", "%28").replace(")", "%29").replace(" ", "%20").replace("<", "%3C").replace(">", "%3E")
        lines += [f"## {markdown_text(job['title'])}", "",
                  f"**{markdown_text(job['company'])}** · {markdown_text(job['location'])}", "",
                  f"Veröffentlicht: {date} · Homeoffice belegt: {'Ja' if job.get('homeoffice') else 'Nein/unklar'} · Bewertung: {rating}", "",
                  markdown_text("; ".join(job['reasons'])), "",
                  f"[Anzeige bei {job['source']} öffnen](<{url}>)", ""]
    if not shown:
        lines += ["Keine passenden Stellen in den abgerufenen Quellen. Dies ist keine Aussage über den gesamten Stellenmarkt.", ""]
    for track, name in track_names.items():
        if not any(job.get("track", "employment") == track for job in shown):
            lines += [f"## {name}", "", "Keine Ergebnisse im aktuellen Abruf.", ""]
    (directory / "report.md").write_text("\n".join(lines), encoding="utf-8")
    from .dashboard import write_dashboard
    write_dashboard(directory, data)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Persönliche regionale Stellensuche und Dashboard")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--pages", type=int, choices=range(1, 11), default=10)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--cache-dir", type=Path, default=Path(".source-cache"))
    parser.add_argument("--skip-remotive", action="store_true", help="Für wiederholte PR-Tests zur Schonung der API")
    parser.add_argument("--diagnostic", action="store_true", help="Expliziter unpersonalisierter Techniktest")
    parser.add_argument("--refresh", action="store_true", help="Quellen neu abrufen; Remotive höchstens einmal pro Tag")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit muss positiv sein")
    if not args.profile and not args.diagnostic:
        parser.error("Persönliches Berufsprofil fehlt. Bitte JOB_PROFILE_JSON hinterlegen. Keine ungefilterte Ersatzsuche gestartet.")
    try:
        profile = validate_profile(json.loads(args.profile.read_text(encoding="utf-8"))) if args.profile else None
        if profile:
            from .focus import prepare_profile
            profile = prepare_profile(profile)
        jobs, statuses = collect(args.pages, args.cache_dir, args.skip_remotive, args.refresh)
        from .pathways import collect_programmes, rank_pathways
        programmes, programme_statuses = collect_programmes(args.cache_dir)
        results = rank_pathways(jobs, profile, programmes)
        vacancies_ok = any(s["ok"] and s["count"] > 0 for s in statuses)
        statuses += programme_statuses
        data = write_report(args.report_dir, results, statuses, profile is not None, len(jobs) + len(programmes), args.limit,
                            profile.get("search_note", "") if profile else "")
        print(f"{data['fetched']} Einträge, {data['matched']} Ergebnisse einschließlich Programme. Bericht: {args.report_dir / 'report.html'}")
        for status in statuses:
            print(f"{status['source']}: {'OK' if status['ok'] else 'ÜBERSPRUNGEN' if status.get('skipped') else 'FEHLER'} ({status['count']})")
        return 0 if vacancies_ok else 1
    except (OSError, ValueError) as error:
        print(f"Konfigurationsfehler: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
