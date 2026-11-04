"""Separate employment listings from qualification and partnership programmes."""
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.request import Request, urlopen

from .__main__ import plain_text

PROGRAMMES = [
    ('GTÜ', 'Selbstständiger GTÜ-Partner werden', 'https://jobs.gtue.de/Selbststaendiger-gtu-partner'),
    ('GTÜ', 'Qualifizierung zum Kfz-Prüfingenieur', 'https://jobs.gtue.de/jobs-partner/qpi'),
    ('KÜS', 'Prüfingenieur werden und selbstständige Perspektiven',
     'https://kues.de/karriere/pruefingenieur-bei-der-kues/pruefingenieur-werden/'),
]


def collect_programmes(cache_dir):
    programmes, statuses = [], []
    for index, (provider, title, url) in enumerate(PROGRAMMES):
        try:
            cache = Path(cache_dir) / f'{datetime.now(timezone.utc).date()}-programme-{index}.html'
            cache.parent.mkdir(parents=True, exist_ok=True)
            if cache.exists():
                html = cache.read_text(encoding='utf-8')
            else:
                with urlopen(Request(url, headers={'User-Agent': 'bewerbungs-agent/0.3'}), timeout=30) as response:
                    html = response.read().decode('utf-8', errors='replace')
                cache.write_text(html, encoding='utf-8')
            html = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', ' ', html, flags=re.I | re.S)
            text = plain_text(html)
            if not any(word in text.casefold() for word in ('prüfingenieur', 'pruefingenieur')):
                raise ValueError('Inhalt nicht mehr als Prüfingenieur-Programm erkennbar')
            programmes.append(dict(title=title, company=provider, source=provider + ' – offizielle Programmseite',
                                   url=url, location='Standort/Verfügbarkeit in München West zu klären',
                                   remote=False, homeoffice=False, published=None, tags=[],
                                   description='', track='self_employment', entry_type='programme', score=None,
                                   reasons=['Qualifizierungs-/Partnerprogramm; keine konkrete freie Stelle und keine lokale Partnerschaft bestätigt.',
                                            'Ingenieurstudium und Kfz-Gutachtertätigkeit sind relevante Ausgangspunkte; Anerkennung des Abschlusses, Fahrerlaubnisse, persönliche Eignung, Qualifizierung und Prüfung müssen mit der Organisation geklärt werden.',
                                            'Keine bestätigte Prüfingenieur-Betrauung aus dem vorliegenden Lebenslauf. Kosten, Dauer, Vereinbarkeit mit Nebengewerbe und selbstständiges Geschäftsmodell prüfen.',
                                            'Das Angestellten-Gehaltsziel und die Homeoffice-Pflicht werden auf diesen Pfad nicht angewendet.']))
            statuses.append(dict(source=provider + ' – ' + title, ok=True, count=1, invalid=0))
        except Exception as error:
            statuses.append(dict(source=provider + ' – ' + title, ok=False, count=0, error=f'{type(error).__name__}: {error}'))
    return programmes, statuses


def rank_pathways(jobs, profile, programmes):
    from .daily import rank
    candidates = rank(jobs, profile)
    if profile and profile.get('focused_search'):
        from .focus import assess
        candidates = [result for job in candidates if (result := assess(job, profile)) is not None]
        candidates.sort(key=lambda job: (job['seniority_status'] == 'experienced', job['score'], job.get('published') or ''), reverse=True)
    employee = [dict(job, track='employment', entry_type='vacancy') for job in candidates]
    self_profile = profile.get('self_employment') if profile else None
    if self_profile:
        independent = rank(jobs, self_profile)
        for job in independent:
            job.update(track='self_employment', entry_type='vacancy')
            job['reasons'].append('Prüfingenieur-Stellenanzeige: Selbstständigkeit/Partnerschaft und Zulassung sind anhand der Originalanzeige zu prüfen.')
    else:
        independent = []
    return employee + independent + programmes
