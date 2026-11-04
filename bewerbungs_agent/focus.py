"""Conservative local/experienced-engineer matching for personalized searches."""
from datetime import datetime
import re
from zoneinfo import ZoneInfo

from .daily import contains

JUNIOR = r'\b(?:junior|trainee|graduate|werkstudent\w*|praktik\w*|internship|ausbildung|berufseinsteiger\w*)\b'


def prepare_profile(profile):
    """Upgrade older profiles; locality is mandatory, never merely a sort key."""
    result = dict(profile)
    region = profile.get('locations') or profile.get('preferred_locations')
    if not region:
        raise ValueError('Für die persönliche Suche fehlt eine verbindliche regionale Ortsliste.')
    result['locations'] = list(region)
    result['focused_search'] = True
    result.setdefault('experienced_only', True)
    result.setdefault('max_age_days', 90)
    result.setdefault('min_competency_groups', 2)
    result.setdefault('excluded_locations', ['Parsdorf', 'Ottobrunn', 'Riem', 'Neubiberg', 'Haar', 'Aschheim', 'Feldkirchen', 'Garching', 'Unterföhring'])
    if profile.get('self_employment'):
        child = dict(profile['self_employment'])
        child['locations'] = list(region)
        child['focused_search'] = False
        result['self_employment'] = child
    return result


def seniority(job):
    title = job['title']
    if re.search(JUNIOR, title, re.I):
        return 'excluded', 'Einstiegs-/Juniorrolle'
    text = job.get('requirements_text') or job['description']
    matches = list(re.finditer(r'\b(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s*\+?\s*(?:years?|jahre[n]?)\b[^.!?]{0,65}?(?:experience|erfahrung)', text, re.I))
    years = max((int(m.group(1)) for m in matches), default=None)
    if re.search(r'\b(?:senior|lead|principal|expert|experte|expertin)\b', title, re.I):
        return 'experienced', 'Senior-/Lead-/Expertenrolle im Titel'
    if years is not None and years >= 3:
        return 'experienced', f'Anzeige nennt mindestens {years} Jahre Erfahrung'
    if re.search(r'mehrjährig\w*\s+(?:einschlägige\s+)?(?:berufs)?erfahrung|several\s+years.{0,35}experience', text, re.I):
        return 'experienced', 'Mehrjährige Erfahrung gefordert; genaue Seniorität prüfen'
    if years is not None and years < 3:
        return 'excluded', f'Erfahrungsanforderung von {years} Jahren unter dem gewählten Erfahrungsniveau'
    return 'unknown', 'Erfahrungsniveau nicht eindeutig belegt'


def local_region(job, profile):
    location = job.get('location', '')
    if any(contains(term, location) for term in profile.get('excluded_locations', [])):
        return False
    # A mention in the description, a source slug or a worldwide remote policy
    # cannot turn an out-of-region posting into a local workplace.
    return any(contains(term, location) for term in profile['locations'])


def assess(job, profile):
    if not local_region(job, profile):
        return None
    level, level_evidence = seniority(job)
    if profile.get('experienced_only', True) and level == 'excluded':
        return None
    published = job.get('published')
    if published:
        age = (datetime.now(ZoneInfo('Europe/Berlin')).date() - datetime.fromisoformat(published).date()).days
        if age < 0 or age > profile.get('max_age_days', 90):
            return None
    roles = [term for term in profile['target_roles'] if contains(term, job['title'])]
    if not roles:
        return None
    text = job['title'] + ' ' + job['description'] + ' ' + ' '.join(job.get('tags', []))
    preferred = any(contains(term, job['title']) for term in profile.get('preferred_roles', []))
    groups = profile.get('competency_groups') or [{'name': term, 'terms': [term]} for term in profile.get('skills', [])]
    matched_groups = [group['name'] for group in groups if any(contains(term, text) for term in group['terms'])]
    if len(matched_groups) < profile.get('min_competency_groups', 2):
        return None
    competencies = round(25 * len(matched_groups) / len(groups)) if groups else 0
    industry_terms = [term for term in profile.get('required_any_keywords', []) if contains(term, text)]
    # No city-centre coordinates or city name can prove a workplace radius.
    region_status = 'Regionaler Ortsname passt; genauer Arbeitsplatz und 20-km-Radius offen'
    gaps = ['Genaue Arbeitgeberadresse und Entfernung im Münchner Westen prüfen.',
            'Gehaltsziel ca. 90.000 EUR/Jahr ist nicht durch die Anzeige bestätigt.']
    if level == 'unknown':
        gaps.append('Erfahrungsniveau mit Arbeitgeber klären; keine priorisierte Empfehlung.')
    experience_points = 20 if level == 'experienced' else 0
    for check in profile.get('experience_checks', []):
        if not any(contains(term, job['title']) for term in check['role_terms']):
            continue
        requirement = re.search(r'\b(\d{1,2})\s*\+?\s*(?:years?|jahre[n]?)\b[^.!?]{0,65}?(?:experience|erfahrung)', job.get('requirements_text') or job['description'], re.I)
        if requirement and int(requirement.group(1)) > check['documented_years']:
            gaps.append(f"Anzeige fordert {requirement.group(1)} Jahre im relevanten Bereich; {check['evidence']}. Die Gesamtberufserfahrung ersetzt diesen Nachweis nicht automatisch.")
            experience_points = min(experience_points, 10)
    if not published:
        gaps.append('Veröffentlichungsdatum fehlt; Aktualität prüfen.')
    components = [
        dict(name='Zielrolle', points=25 if preferred else 15, maximum=25, evidence=', '.join(roles)),
        dict(name='Berufserfahrung', points=experience_points, maximum=20, evidence=level_evidence + ('; geforderte Spezialerfahrung nicht vollständig belegt' if experience_points == 10 else '')),
        dict(name='Kernkompetenzen', points=competencies, maximum=25, evidence=', '.join(matched_groups) or 'Keine Gruppe im Anzeigentext belegt'),
        dict(name='Zielbranche', points=10 if industry_terms else 0, maximum=10, evidence=', '.join(industry_terms) or 'Branche nicht belegt'),
        dict(name='Homeoffice', points=10 if job.get('homeoffice') else 0, maximum=10, evidence=job.get('homeoffice_evidence', 'Nicht belegt')),
        dict(name='Arbeitsort', points=5, maximum=10, evidence=region_status),
    ]
    score = sum(component['points'] for component in components)
    label = 'Starker Profilabgleich' if score >= 80 else 'Guter Profilabgleich' if score >= 70 else 'Teilweise passend' if score >= 55 else 'Geringe fachliche Übereinstimmung'
    return dict(job, score=score, score_label=label, score_components=components,
                seniority_status=level, seniority_evidence=level_evidence,
                region_status=region_status, radius_verified=False, gaps=gaps,
                review_required=True, matched_competencies=matched_groups,
                reasons=[f"{component['name']}: {component['evidence']}" for component in components] + gaps)
