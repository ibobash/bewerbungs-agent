from contextlib import redirect_stderr
import io
import unittest
from unittest.mock import patch

from bewerbungs_agent.daily import main, normalize
from bewerbungs_agent.focus import assess, prepare_profile


class FocusTests(unittest.TestCase):
    def setUp(self):
        self.profile = prepare_profile(dict(
            target_roles=['Systems Engineer', 'Requirements Engineer'],
            preferred_roles=['Systems Engineer'], preferred_locations=['Munich', 'München', 'Germering'],
            homeoffice_required=True, skills=['DOORS', 'Integration'],
            required_any_keywords=['Robotics'], competency_groups=[
                dict(name='Requirements', terms=['DOORS']), dict(name='Integration', terms=['Integration'])]))
        self.job = normalize(dict(title='Senior Systems Engineer', company_name='Example',
                                  location='Munich', remote=True, description='Robotics: DOORS und Integration.',
                                  url='https://example.org/job'), 'Arbeitnow')

    def test_other_cities_and_unknown_locations_are_not_regional_matches(self):
        for location in ['Berlin', 'Hamburg', 'Zürich', 'Worldwide', 'Nicht angegeben', 'Munich Riem']:
            self.assertIsNone(assess(dict(self.job, location=location), self.profile))
        # Munich in the job text does not turn a Berlin workplace into a local job.
        self.assertIsNone(assess(dict(self.job, location='Berlin', description='Our Munich team uses DOORS Integration'), self.profile))

    def test_regional_name_does_not_establish_workplace_radius(self):
        result = assess(self.job, self.profile)
        self.assertFalse(result['radius_verified'])
        self.assertTrue(result['review_required'])
        self.assertEqual(result['score'], sum(c['points'] for c in result['score_components']))
        self.assertEqual(result['score_components'][-1]['points'], 5)

    def test_no_junior_or_unrelated_roles_even_with_keyword_matches(self):
        for title in ['Junior Systems Engineer', 'Graduate Systems Engineer', 'Werkstudent Systems Engineer']:
            self.assertIsNone(assess(dict(self.job, title=title), self.profile))
        self.assertIsNone(assess(dict(self.job, description='A medical company with DOORS but unrelated duties'), self.profile))

    def test_missing_seniority_is_a_review_case(self):
        result = assess(dict(self.job, title='Systems Engineer'), self.profile)
        self.assertEqual(result['seniority_status'], 'unknown')
        self.assertEqual(result['score_components'][1]['points'], 0)

    def test_specific_experience_is_not_replaced_by_total_career_length(self):
        profile = dict(self.profile, experience_checks=[dict(role_terms=['Requirements Engineer'],
                       documented_years=3, evidence='Requirements-Rolle seit 2023')])
        result = assess(dict(self.job, title='Senior Requirements Engineer',
                             requirements_text='Minimum 8 years of professional experience in requirements engineering'), profile)
        self.assertEqual(result['score_components'][1]['points'], 10)
        self.assertTrue(any('8 Jahre' in gap for gap in result['gaps']))

    def test_missing_profile_stops_before_any_source_is_called(self):
        with patch('bewerbungs_agent.daily.collect') as collect, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main([])
        self.assertEqual(error.exception.code, 2)
        collect.assert_not_called()

    def test_legacy_profiles_gain_hard_regional_filter_for_both_paths(self):
        result = prepare_profile(dict(target_roles=['Systems Engineer'], preferred_locations=['Munich'],
                                      self_employment=dict(target_roles=['Prüfingenieur'])))
        self.assertEqual(result['locations'], ['Munich'])
        self.assertEqual(result['self_employment']['locations'], ['Munich'])
        self.assertNotIn('homeoffice_required', result['self_employment'])


if __name__ == '__main__':
    unittest.main()
