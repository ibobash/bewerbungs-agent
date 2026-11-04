"""Standalone interactive dashboard; all external text is escaped."""
from html import escape
from pathlib import Path


def write_dashboard(directory, data):
    jobs = data['jobs']
    employee = [j for j in jobs if j.get('track', 'employment') == 'employment']
    verified_radius = sum(bool(j.get('radius_verified')) for j in employee)
    programmes = sum(j.get('entry_type') == 'programme' for j in jobs)
    cards = []
    for job in jobs:
        score = job.get('score')
        programme = job.get('entry_type') == 'programme'
        track = job.get('track', 'employment')
        seniority = job.get('seniority_status', 'unknown')
        band = 'strong' if score is not None and score >= 80 else 'good' if score is not None and score >= 70 else 'partial'
        label = job.get('score_label', 'Profilabgleich' if score is not None else 'Nicht bewertet')
        if programme:
            label = 'Qualifizierung / Partnerschaft'
        tags = ['Programm – keine freie Stelle'] if programme else [
            'Berufserfahrung belegt' if seniority == 'experienced' else 'Erfahrungsniveau offen',
            '20-km-Radius offen' if not job.get('radius_verified') else '20-km-Radius bestätigt',
            'Homeoffice-Hinweis' if job.get('homeoffice') else 'Homeoffice offen',
        ]
        components = ''.join(f'<div class="component"><div><b>{escape(c["name"])}</b><span>{c["points"]}/{c["maximum"]}</span></div>'
                             f'<progress value="{c["points"]}" max="{c["maximum"]}"></progress><small>{escape(c["evidence"])}</small></div>'
                             for c in job.get('score_components', []))
        gaps = job.get('gaps', [])
        if programme:
            gaps = job.get('reasons', [])
        gap_html = ''.join(f'<li>{escape(gap)}</li>' for gap in gaps)
        if not components and not programme:
            components = '<p>' + escape('; '.join(job.get('reasons', []))) + '</p>'
        score_html = f'<div class="score {band}"><strong>{score}</strong><span>/100</span></div>' if score is not None else '<div class="score neutral">—</div>'
        searchable = ' '.join((job['title'], job['company'], job['location'], job['source']))
        cards.append(
            f'<article class="job" data-track="{escape(track, quote=True)}" data-seniority="{escape(seniority, quote=True)}" '
            f'data-score="{score if score is not None else -1}" data-radius="{str(bool(job.get("radius_verified"))).lower()}" '
            f'data-date="{escape(job.get("published") or "", quote=True)}" data-search="{escape(searchable.casefold(), quote=True)}">'
            f'<div class="cardtop"><div><p class="company">{escape(job["company"])}</p><h2>{escape(job["title"])}</h2>'
            f'<p class="meta">{escape(job["location"])} · Veröffentlicht: {escape(job.get("published") or "Nicht angegeben")}</p></div>{score_html}</div>'
            f'<p class="rating">{escape(label)}</p><div class="tags">' + ''.join(f'<span>{escape(tag)}</span>' for tag in tags) + '</div>'
            f'<details><summary>Bewertung und offene Punkte ansehen</summary><div class="components">{components}</div>'
            + (f'<div class="gaps"><b>Noch zu prüfen</b><ul>{gap_html}</ul></div>' if gap_html else '') + '</details>'
            f'<a class="link" href="{escape(job["url"], quote=True)}" target="_blank" rel="noopener">'
            f'{"Programm" if programme else "Stelle"} bei {escape(job["source"])} öffnen ↗</a></article>')
    source_rows = ''.join(f'<li><span class="dot {"ok" if s["ok"] else "skip" if s.get("skipped") else "fail"}"></span>'
                          f'<b>{escape(s["source"])}</b> — ' + (f'{s["count"]} Einträge' if s['ok'] else escape(s.get('error', 'Nicht verfügbar'))) + '</li>'
                          for s in data['sources'])
    mode = '' if data['personalized'] else '<div class="notice">TECHNISCHER TEST OHNE BERUFSPROFIL · Dies sind keine persönlichen Empfehlungen.</div>'
    criteria = escape(data.get('search_note', ''))
    title = 'Dein nächster beruflicher Schritt.'
    document = '''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Karriere-Dashboard</title><style>
:root{--ink:#18283b;--muted:#56657a;--line:#dce3eb;--teal:#096f65;--bg:#f3f6f8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}header{background:#10283a;color:#fff;padding:40px max(24px,calc((100vw - 1100px)/2)) 45px}header small{color:#a7d9d1;text-transform:uppercase;letter-spacing:.13em}h1{font-size:clamp(30px,4vw,46px);line-height:1.18;margin:12px 0 18px;letter-spacing:-.035em}header p{color:#d5e0e8;max-width:850px}.stamp{font-size:13px;opacity:.8}main{max-width:1148px;margin:auto;padding:28px 24px 64px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:0 0 24px}.stat{min-width:0;overflow-wrap:anywhere;background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 22px}.stat strong{font-size:34px;display:block;line-height:1.2}.stat span{font-size:14px;color:var(--muted)}.filters{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px;display:flex;gap:12px;flex-wrap:wrap;align-items:end;position:sticky;top:8px;z-index:2;box-shadow:0 4px 18px #10283a0a}label{font-size:13px;color:var(--muted);display:flex;gap:5px;flex-direction:column}input,select{font:inherit;color:var(--ink);padding:10px;border:1px solid #c7d1dd;border-radius:7px;background:#fff}input[type=search]{width:240px}label.check{flex-direction:row;align-items:center;padding-bottom:10px}.notice{padding:16px 20px;border:1px solid #e3b776;background:#fff4de;border-radius:10px;margin-bottom:20px}.explain{font-size:14px;color:var(--muted);margin:22px 0}.explain summary{cursor:pointer;font-weight:600}.count{display:flex;justify-content:space-between;margin:24px 0 12px;gap:12px}.job{padding:26px;background:#fff;border:1px solid var(--line);border-radius:12px;margin:16px 0}.cardtop>div:first-child{min-width:0;overflow-wrap:anywhere}.cardtop{display:flex;gap:22px;justify-content:space-between}.company{font-size:14px;font-weight:650;color:var(--teal);margin:0 0 5px}h2{font-size:22px;line-height:1.35;margin:0 0 10px}.meta{font-size:14px;color:var(--muted);margin:0}.score{min-width:88px;text-align:right;font-variant-numeric:tabular-nums}.score strong{font-size:42px;line-height:1.1}.score span{display:block;font-size:13px;color:var(--muted)}.strong{color:#09664d}.good{color:#1a627b}.partial{color:#8a5b1b}.neutral{font-size:30px;color:var(--muted)}.rating{font-weight:600;margin:15px 0 10px}.tags{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}.tags span{background:#edf3f5;padding:4px 10px;border-radius:5px;font-size:12px}.job details{border-top:1px solid var(--line);padding-top:14px;font-size:14px}.job summary{cursor:pointer;color:var(--muted)}.components{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:22px 0}.component>div{display:flex;justify-content:space-between;gap:10px}.component small{color:var(--muted);display:block;overflow-wrap:anywhere}progress{width:100%;height:7px;accent-color:var(--teal)}.gaps{background:#fff8e9;padding:16px;border-radius:8px}.gaps ul{padding-left:20px;margin-bottom:0}.link{display:inline-block;margin-top:20px;color:var(--teal);font-weight:650;text-decoration:none}.link:hover{text-decoration:underline}.sources{margin-top:30px;padding:22px;background:#fff;border:1px solid var(--line);border-radius:12px;font-size:14px}.sources ul{list-style:none;padding:0}.sources li{margin:9px 0}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px}.ok{background:#147d65}.skip{background:#ae7d28}.fail{background:#b14848}[hidden]{display:none!important}#empty{padding:32px;background:white;border:1px dashed #b9c6d3;border-radius:12px;color:var(--muted)}footer{font-size:13px;color:var(--muted);margin-top:30px}@media(max-width:650px){header{padding:28px 20px}.stats{gap:8px}.stat{padding:12px}.stat strong{font-size:27px}.stat span{font-size:12px}.filters{position:static}input[type=search]{width:100%}.filters label{flex:1 1 150px}.job{padding:18px}.components{grid-template-columns:1fr}h2{font-size:19px}.score strong{font-size:34px}}
</style></head><body>'''
    document += (f'<header><small>Karriere · München West</small><h1>{title}</h1><p>Ingenieurrollen mit Berufserfahrung, regionaler Vorauswahl und transparenter Bewertung. '
                 'Selbstständigkeit als Prüfingenieur bleibt ein eigener Suchpfad.</p><div class="stamp">Stand: '
                 f'{escape(data["generated_at"])} · {data["fetched"]} Einträge abgerufen</div></header><main>{mode}'
                 f'<section class="stats"><div class="stat"><strong>{verified_radius}</strong><span>Im 20-km-Radius bestätigt</span></div>'
                 f'<div class="stat"><strong>{len(employee)}</strong><span>Regionale Prüfungskandidaten</span></div>'
                 f'<div class="stat"><strong>{programmes}</strong><span>Qualifizierungs-/Partnerprogramme</span></div></section>'
                 '<div class="notice"><b>Entfernung und Gehalt offen.</b> Ein Ortsname wie München bestätigt keinen Arbeitsplatz im 20-km-Radius. '
                 'Regionale Kandidaten sind eine Prüfliste; 90.000 € sind dein Ziel, kein bestätigtes Angebot.</div>'
                 '<section class="filters" aria-label="Ergebnisse filtern"><label>Suchen<input id="query" type="search" placeholder="Firma oder Position"></label>'
                 '<label>Suchpfad<select id="track"><option value="employment">Anstellung</option><option value="self_employment">Prüfingenieur / Selbstständigkeit</option><option value="all">Beide Pfade</option></select></label>'
                 '<label>Eignungsskala<select id="minimum"><option value="0">Alle Bewertungen</option><option value="55">Ab 55 Punkten</option><option value="70">Ab 70 Punkten</option><option value="80">Ab 80 Punkten</option></select></label>'
                 '<label>Sortierung<select id="sort"><option value="score">Beste Passung zuerst</option><option value="date">Neueste zuerst</option></select></label>'
                 '<label class="check"><input id="unknown" type="checkbox">Erfahrungsniveau offen einblenden</label></section>'
                 '<details class="explain"><summary>Suchprofil und Bedeutung der Skala</summary>'
                 f'<p>{criteria}</p><p>Die 100 Punkte setzen sich zusammen aus Zielrolle (25), Berufserfahrung (20), Kernkompetenzen (25), Zielbranche (10), Homeoffice (10) und Arbeitsort (10). '
                 'Ein Ortsname allein erhält nur 5 Ortspunkte. Ab 80: starker, ab 70: guter, ab 55: teilweiser Profilabgleich. '
                 'Die Skala ist ein regelbasierter Profilabgleich und keine Bewerbungs-Erfolgswahrscheinlichkeit. Gehalt und fachliche Detailanforderungen separat prüfen. '
                 'Programme erhalten keinen Eignungsscore.</p></details>'
                 '<div class="count"><b id="count" aria-live="polite">Ergebnisse</b><span>Nur die gewählte Region</span></div>'
                 '<section id="jobs">' + ''.join(cards) + '</section><p id="empty" hidden>Keine Treffer für diese Filter. '
                 'Die Suche wird nicht auf ganz Deutschland ausgeweitet. Prüfe bei Bedarf die regionale Prüfliste mit offenem Erfahrungsniveau.</p>'
                 '<details class="sources"><summary>Quellen und Abrufstatus</summary><ul>' + source_rows + '</ul></details>'
                 '<footer>Für eine neue Suche schreibe im Chat: <b>„Starte eine neue Suche“</b>. Dieses Dashboard ist eine Momentaufnahme. '
                 'Offizielle Programme bestätigen keine lokale Partnerschaft oder persönliche Prüfingenieur-Zulassung. '
                 '<a href="https://www.gesetze-im-internet.de/stvzo_2012/anlage_viiib.html">Voraussetzungen nach Anlage VIIIb StVZO</a>.</footer></main>')
    document += '''<script>
const controls = ['query','track','minimum','sort','unknown'].map(id=>document.getElementById(id));
const [query,track,minimum,sort,unknown] = controls;
const cards = Array.from(document.querySelectorAll('.job'));
function update(){
 const text=query.value.trim().toLocaleLowerCase('de'); let count=0;
 cards.sort((a,b)=>sort.value==='date' ? b.dataset.date.localeCompare(a.dataset.date) : Number(b.dataset.score)-Number(a.dataset.score));
 for(const card of cards){
  const programme=Number(card.dataset.score)<0;
  const visible=(track.value==='all'||card.dataset.track===track.value)&&card.dataset.search.includes(text)&&
   (Number(minimum.value)===0||(!programme&&Number(card.dataset.score)>=Number(minimum.value)))&&
   (card.dataset.track!=='employment'||unknown.checked||card.dataset.seniority==='experienced');
  card.hidden=!visible; if(visible) count++;
  document.getElementById('jobs').appendChild(card);
 }
 document.getElementById('count').textContent=count+' Ergebnisse angezeigt';
 document.getElementById('empty').hidden=count!==0;
}
controls.forEach(control=>control.addEventListener('input',update));update();
</script></body></html>'''
    for name in ('dashboard.html', 'report.html'):
        (Path(directory) / name).write_text(document, encoding='utf-8')
