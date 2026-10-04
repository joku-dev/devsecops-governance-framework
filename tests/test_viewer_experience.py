"""A presentation must not invent a closure or trust an unvalidated projection."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.viewer_experience import load_consumer_case
from lib.governance_lifecycle.consumer_acceptance import validate


class ViewerExperienceTests(unittest.TestCase):
    def test_case_matches_accepted_projection_and_links_retained_records(self):
        expected = validate(ROOT)
        result = load_consumer_case(ROOT)
        self.assertTrue(result['available'])
        self.assertEqual(expected['finding_state'], result['finding_state'])
        self.assertEqual(expected['counts'], result['counts'])
        self.assertEqual(result['counts']['receipts'] + result['counts']['actions'], len(result['timeline']))
        self.assertTrue(all((ROOT / entry['source_file']).is_file() for entry in result['timeline']))
        self.assertEqual(sorted(x['recorded_at'] for x in result['timeline']), [x['recorded_at'] for x in result['timeline']])

    def test_invalid_projection_never_becomes_zero_cases_or_closed(self):
        with patch('lib.viewer_experience.validate', side_effect=ValueError('Projection differs')):
            self.assertEqual({'available': False}, load_consumer_case(ROOT))

    def test_missing_source_is_unavailable(self):
        with patch('lib.viewer_experience.validate', side_effect=FileNotFoundError('Missing ledger')):
            self.assertEqual({'available': False}, load_consumer_case(ROOT))
