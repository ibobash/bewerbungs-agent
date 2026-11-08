"""Local, explainable CV checks. No uploads and no simulated ATS score."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def extract(path):
    path = Path(path)
    suffix = path.suffix.lower()
    metadata = {'format': suffix.lstrip('.'), 'tables': None, 'images': None}
    if suffix in {'.txt', '.md'}:
        return path.read_text(encoding='utf-8-sig'), metadata
    if suffix == '.pdf':
        if not shutil.which('pdftotext'):
            raise ValueError('PDF benötigt das lokale Programm pdftotext (Poppler). Alternativ DOCX oder TXT verwenden.')
        result = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(path.resolve()), '-'],
                                capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('PDF konnte nicht ausgelesen werden; Verschlüsselung oder beschädigte Datei prüfen.')
        return result.stdout.decode('utf-8'), metadata
    if suffix not in {'.docx', '.pptx'}:
        raise ValueError('Unterstützt werden PDF, DOCX, PPTX, TXT und Markdown.')
    with ZipFile(path) as archive:
        if suffix == '.docx':
            root = ET.fromstring(archive.read('word/document.xml'))
            text = '\n'.join(''.join(t.text or '' for t in p.iter(W + 't'))
                             for p in root.iter(W + 'p'))
            metadata['tables'] = len(list(root.iter(W + 'tbl')))
            metadata['images'] = len(list(root.iter(W + 'drawing')))
            metadata['header_footer_parts'] = sum(bool(re.fullmatch(r'word/(?:header|footer)\d+\.xml', n)) for n in archive.namelist())
        else:
            names = sorted((n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                           key=lambda n: int(re.search(r'slide(\d+)', n).group(1)))
            parts = []
            metadata['tables'] = 0
            for name in names:
                root = ET.fromstring(archive.read(name))
                parts.append('\n'.join(''.join(t.text or '' for t in p.iter(A + 't'))
                                       for p in root.iter(A + 'p')))
                metadata['tables'] += len(list(root.iter(A + 'tbl')))
            text = '\n'.join(parts)
            metadata['pages'] = len(names)
    return text, metadata


def has_term(term, text):
    normalized = ' '.join(text.casefold().split())
    term = ' '.join(term.casefold().split())
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', normalized))


def check(text, metadata, keywords=()):
    findings = []
    def add(level, code, message):
        findings.append({'severity': level, 'code': code, 'message': message})
    if metadata['format'] == 'pptx':
        add('warning', 'presentation', 'PPTX wird in vielen Bewerbungsportalen nicht akzeptiert. DOCX oder ein textbasiertes PDF gemäß Portalvorgabe einreichen; den Export erneut prüfen.')
    if len(re.sub(r'\s', '', text)) < 100:
        add('error', 'little_text', 'Kaum auslesbarer Text: möglicherweise Scan/Bild oder unvollständiger Export. OCR bzw. Textdatei erforderlich; weitere Inhaltsprüfungen sind nicht belastbar.')
    else:
        if not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text):
            add('warning', 'email', 'Keine E-Mail-Adresse im ausgelesenen Haupttext erkannt.')
        sections = {
            'Berufserfahrung': r'\b(?:berufserfahrung|erfahrung|beruflicher werdegang|experience|employment)\b',
            'Ausbildung/Studium': r'\b(?:bildung|ausbildung|studium|education|qualifications)\b',
            'Kompetenzen': r'\b(?:fähigkeiten|kenntnisse|kompetenzen|kernkompetenzen|skills|tools)\b',
        }
        for label, pattern in sections.items():
            if not re.search(pattern, text, re.I):
                add('info', 'section', f'Übliche Überschrift für {label} nicht erkannt; eindeutige Abschnittstitel verwenden.')
        if not re.search(r'\b(?:0?[1-9]|1[0-2])[./]\d{4}\b|\b(?:19|20)\d{2}\s*[-–]', text):
            add('info', 'dates', 'Keine üblichen Beschäftigungszeiträume erkannt; einheitlich MM/JJJJ verwenden.')
    if metadata.get('tables'):
        add('warning', 'tables', 'Tabellen erkannt: Lesereihenfolge im Textauszug prüfen; einspaltiges Layout bevorzugen.')
    if metadata.get('header_footer_parts'):
        add('info', 'headers', 'Kopf-/Fußzeilen vorhanden und nicht im Haupttextauszug enthalten. Wichtige Kontaktdaten zusätzlich im Haupttext platzieren.')
    add('info', 'reading_order', 'Textauszug mit dem sichtbaren Dokument vergleichen: Spalten, Textfelder und Symbole können die Lesereihenfolge verändern. Eine visuelle Layoutprüfung ist nicht enthalten.')
    terms = list(dict.fromkeys(t.strip() for t in keywords if t.strip()))
    matched = [t for t in terms if has_term(t, text)]
    missing = [t for t in terms if t not in matched]
    return {
        'assessment': 'Regelbasierte Hinweise; kein universeller ATS-Score und keine Einstellungsprognose.',
        'document': metadata,
        'findings': findings,
        'keyword_check': {'requested': terms, 'found': matched, 'not_found': missing,
                          'note': 'Wortabgleich ohne semantische Bewertung. Nicht gefunden bedeutet nicht fehlende Qualifikation. Nur belegbare Kenntnisse ergänzen.'},
        'text': text,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Lebenslauf lokal auf ATS-Lesbarkeit prüfen.')
    parser.add_argument('cv', type=Path)
    parser.add_argument('--keywords', nargs='*', default=[], help='Explizite Begriffe aus der Zielanzeige; Mehrwortbegriffe in Anführungszeichen.')
    parser.add_argument('--output', type=Path, help='Privater JSON-Bericht inklusive ausgelesenem CV-Text; außerhalb des öffentlichen Repositorys speichern.')
    args = parser.parse_args(argv)
    try:
        text, metadata = extract(args.cv)
        report = check(text, metadata, args.keywords)
        output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding='utf-8')
            args.output.chmod(0o600)
            print(f'Privater ATS-Bericht: {args.output}')
        else:
            print(output)
        return 0
    except (OSError, ValueError, BadZipFile, KeyError, ET.ParseError, subprocess.TimeoutExpired) as error:
        print(f'ATS-Prüfung fehlgeschlagen: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
