import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from bewerbungs_agent.ats import check, extract, main


class AtsTests(unittest.TestCase):
    def test_keyword_boundaries_and_no_invented_score(self):
        report = check('Skills: CANalyzer, IBM\nDOORS, C++', {'format': 'txt'}, ['CAN', 'IBM DOORS', 'C++'])
        self.assertEqual(report['keyword_check']['found'], ['IBM DOORS', 'C++'])
        self.assertEqual(report['keyword_check']['not_found'], ['CAN'])
        self.assertNotIn('score', report)

    def test_scanned_document_warns_without_false_contact_findings(self):
        report = check('', {'format': 'pdf'})
        codes = [f['code'] for f in report['findings']]
        self.assertIn('little_text', codes)
        self.assertNotIn('email', codes)

    def test_docx_runs_remain_in_one_word_and_tables_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cv.docx'
            with ZipFile(path, 'w') as z:
                z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Require</w:t></w:r><w:r><w:t>ments</w:t></w:r></w:p><w:tbl/></w:body></w:document>')
            text, metadata = extract(path)
            self.assertEqual(text, 'Requirements')
            self.assertEqual(metadata['tables'], 1)

    def test_pptx_slides_use_numeric_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cv.pptx'
            with ZipFile(path, 'w') as z:
                for n in [10, 2, 1]:
                    z.writestr(f'ppt/slides/slide{n}.xml', f'<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r><a:t>Seite {n}</a:t></a:r></a:p>')
            text, metadata = extract(path)
            self.assertEqual(text, 'Seite 1\nSeite 2\nSeite 10')
            self.assertEqual(metadata['pages'], 3)

    def test_missing_or_corrupt_input_returns_error(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(Path(folder) / 'missing.pdf')]), 1)
            bad = Path(folder) / 'bad.docx'
            bad.write_text('not a zip')
            self.assertEqual(main([str(bad)]), 1)


if __name__ == '__main__':
    unittest.main()
