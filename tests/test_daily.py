import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bewerbungs_agent.daily import collect, contains, normalize, publication, rank, validate_profile, write_report


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.raw = dict(title='Requirements Engineer', company_name='Beispiel', location='München',
                        remote=True, created_at=1793790000, url='https://example.org/job',
                        description='<p>IBM DOORS und ISO 26262 in der Fahrzeugentwicklung</p>', tags=[])
        self.job = normalize(self.raw, 'Arbeitnow')
        self.profile = dict(target_roles=['Requirements Engineer'], skills=['DOORS', 'ISO 26262'],
                            locations=['München'], remote_only=True)

    def test_real_profile_match_and_explanations(self):
        result = rank([self.job], self.profile)
        self.assertEqual(result[0]['score'], 100)
        self.assertIn('DOORS', result[0]['reasons'][1])
        self.assertEqual(rank([dict(self.job, location='Berlin')], self.profile), [])
        self.assertEqual(rank([dict(self.job, remote=False)], self.profile), [])
        self.assertFalse(contains('CAN', 'candidate'))
        self.assertFalse(contains('SQL', 'NoSQL'))

    def test_unpersonalized_not_scored(self):
        self.assertIsNone(rank([self.job], None)[0]['score'])
        with self.assertRaises(ValueError):
            validate_profile({'target_roles': []})
        with self.assertRaises(ValueError):
            validate_profile({'target_roles': 'Engineer'})

    def test_required_and_excluded_criteria(self):
        self.assertEqual(rank([self.job], dict(self.profile, required_keywords=['Simulink'])), [])
        self.assertEqual(rank([self.job], dict(self.profile, exclude_keywords=['Fahrzeugentwicklung'])), [])
        self.assertEqual(rank([self.job], dict(self.profile, required_any_keywords=['Luftfahrt'])), [])

    def test_date_and_url_integrity(self):
        self.assertEqual(publication('2026-11-02T20:01:00'), '2026-11-02')
        self.assertIsNone(publication('unknown'))
        with self.assertRaises(ValueError):
            normalize(dict(self.raw, url='javascript:alert(1)'), 'Arbeitnow')

    @patch('bewerbungs_agent.daily.request_json')
    @patch('bewerbungs_agent.daily.fetch_jobs')
    def test_partial_failure_keeps_other_sources_and_deduplicates(self, arbeitnow, request):
        arbeitnow.return_value = [self.raw, self.raw]
        request.side_effect = [TimeoutError('source timed out'), []]
        jobs, statuses = collect()
        self.assertEqual(len(jobs), 1)
        self.assertFalse(statuses[1]['ok'])
        self.assertTrue(statuses[0]['ok'])

    def test_report_escapes_external_content_and_marks_unknown_date(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs = rank([dict(self.job, title='<script>alert(1)</script>', published=None)], None)
            write_report(Path(directory), jobs, [], False, 1)
            html = (Path(directory) / 'report.html').read_text()
            self.assertNotIn('<script>alert(1)</script>', html)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
            self.assertIn('Nicht angegeben', html)
            self.assertIn('Berufsprofil fehlt', html)
            data = json.loads((Path(directory) / 'results.json').read_text())
            self.assertIsNone(data['jobs'][0]['score'])


class PreferenceTests(unittest.TestCase):
    def test_each_path_remains_visible_when_report_limit_is_reached(self):
        job = normalize(dict(title='Project Engineer', company_name='Example', location='Munich',
                             remote=True, url='https://example.org/job', description='', tags=[]), 'Arbeitnow')
        employee = dict(job, score=60, reasons=['Textabgleich'], track='employment')
        programme = dict(job, score=None, reasons=['Voraussetzungen offen'], track='self_employment', entry_type='programme')
        with tempfile.TemporaryDirectory() as directory:
            data = write_report(Path(directory), [employee, employee, programme], [], True, 3, limit=1)
            self.assertEqual(len(data['jobs']), 2)
            self.assertEqual(data['jobs'][1]['track'], 'self_employment')
            self.assertIsNone(data['jobs'][1]['score'])

    def test_homeoffice_is_not_hybrid_vehicle_technology(self):
        from bewerbungs_agent.daily import home_office
        self.assertFalse(home_office('Entwicklung von Hybrid-Antrieben')[0])
        self.assertTrue(home_office('Flexible hours and hybrid work model within Germany')[0])
        self.assertFalse(home_office('Homeoffice ist nicht möglich', remote=True)[0])
        self.assertFalse(home_office('Kein Anspruch auf Homeoffice')[0])

    def test_independent_path_does_not_inherit_employee_salary_or_homeoffice(self):
        from bewerbungs_agent.pathways import rank_pathways
        job = normalize(dict(title='Kfz-Prüfingenieur', company_name='Prüfbüro', location='München',
                             remote=False, url='https://example.org/job', description='Hauptuntersuchung nach StVZO', tags=[]), 'Arbeitnow')
        profile = dict(target_roles=['Systemingenieur'], homeoffice_required=True, salary_target_eur=90000,
                       self_employment=dict(target_roles=['Kfz-Prüfingenieur']))
        results = rank_pathways([job], profile, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['track'], 'self_employment')
        self.assertNotIn('Gehaltsziel', ' '.join(results[0]['reasons']))

    @patch('bewerbungs_agent.daily.fetch_brainlab', return_value=[])
    @patch('bewerbungs_agent.daily.request_json')
    @patch('bewerbungs_agent.daily.fetch_jobs')
    def test_same_day_cache_avoids_repeated_api_calls(self, arbeitnow, request, brainlab):
        arbeitnow.return_value = []
        request.side_effect = [{'jobs': []}, []]
        with tempfile.TemporaryDirectory() as directory:
            collect(cache_dir=Path(directory))
            collect(cache_dir=Path(directory))
        self.assertEqual(arbeitnow.call_count, 1)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(brainlab.call_count, 1)


if __name__ == '__main__':
    unittest.main()
