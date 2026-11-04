import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_jobs(pages=1):
    jobs = {}
    for page in range(1, pages + 1):
        request = Request(f"{API_URL}?page={page}", headers={
            "User-Agent": "bewerbungs-agent/0.1", "Accept": "application/json"
        })
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        if not isinstance(payload.get("data"), list):
            raise ValueError("Die Stellen-API liefert kein gültiges data-Array.")
        for job in payload["data"]:
            jobs[job["slug"]] = job
        if not payload["data"] or not payload.get("links", {}).get("next"):
            break
    return list(jobs.values())


def plain_text(value):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def select_jobs(jobs, keywords=(), location="", remote=False):
    terms = list(dict.fromkeys(term.strip().casefold() for term in keywords if term.strip()))
    results = []
    for job in jobs:
        description = plain_text(job.get("description", ""))
        searchable = " ".join([job.get("title", ""), description,
                               " ".join(job.get("tags", []))]).casefold()
        matches = [term for term in terms if term in searchable]
        if terms and not matches:
            continue
        if location.casefold() not in job.get("location", "").casefold():
            continue
        if remote and not job.get("remote", False):
            continue
        results.append({
            "title": job["title"], "company": job["company_name"],
            "location": job.get("location", ""), "remote": bool(job.get("remote")),
            "url": job["url"], "description": description,
            "matched_keywords": matches,
            "score": round(100 * len(matches) / len(terms)) if terms else 0,
            "source": "arbeitnow", "created_at": job.get("created_at"),
        })
    return sorted(results, key=lambda job: job["score"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Aktuelle Stellen suchen und mit Stichwörtern abgleichen.")
    parser.add_argument("--keywords", nargs="*", default=[])
    parser.add_argument("--location", default="")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--pages", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit muss mindestens 1 sein")
    try:
        jobs = select_jobs(fetch_jobs(args.pages), args.keywords, args.location, args.remote)
        output = json.dumps(jobs[:args.limit], ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        print(f"{len(jobs)} passende Stellen gefunden.", file=sys.stderr)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        print(f"Stellensuche fehlgeschlagen: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
