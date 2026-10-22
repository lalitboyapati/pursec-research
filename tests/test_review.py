import json
import tempfile
import unittest
from pathlib import Path
from pursec_scraper.review import prepare, summarize, validate_verdict, wilson, evidence_flags

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root/'run'; self.run.mkdir()
        self.out = self.root/'review'
        rows = [dict(title=f'Paper {i}', venue='usenix', year=2024,
                     verification='title_venue_year_matched' if i < 10 else 'unverified',
                     authors=[], source_url=f'https://example.org/{i}') for i in range(11)]
        (self.run/'papers.json').write_text(json.dumps(rows))
        (self.run/'reference.json').write_text(json.dumps(dict(papers=rows[:10], venue='usenix', year=2024, source_url='https://example.org')))
        (self.run/'missing-from-discovery.json').write_text('[]')
        prepare(self.run,self.out,5,42)

    def test_reproducible_sample_and_targeted_separation(self):
        other=self.root/'other'; prepare(self.run,other,5,42)
        a=json.loads((self.out/'selection.json').read_text())
        b=json.loads((other/'selection.json').read_text())
        self.assertEqual(a['records'],b['records'])
        stats=summarize(self.out)
        self.assertEqual(stats['sample_size'],5)
        self.assertEqual(stats['targeted_records'],1)
        self.assertIsNone(stats['human_membership_accuracy_within_automatically_matched_stratum'])

    def test_no_overwrite(self):
        with self.assertRaises(ValueError): prepare(self.run,self.out)

    def test_completed_random_sample_excludes_targeted_failure(self):
        path=self.out/'human-review.json'; data=json.loads(path.read_text())
        for row in data['records']:
            row['reviewer']='Tester'; row['checked_at']='2026-10-22'
            row['decisions']['membership']='correct' if 'random_matched_sample' in row['selection'] else 'incorrect'
        path.write_text(json.dumps(data))
        stats=summarize(self.out)
        self.assertEqual(stats['human_membership_accuracy_within_automatically_matched_stratum'],1)
        self.assertLess(stats['wilson_95_interval'][0],1)

    def test_reviewer_and_sampling_integrity(self):
        path=self.out/'human-review.json'; data=json.loads(path.read_text())
        data['records'][0]['decisions']['membership']='correct'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): summarize(self.out)
        data['records'][0]['decisions']['membership']='pending'
        data['records'][0]['selection']=['unmatched']
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): summarize(self.out)

    def test_model_must_cite_real_evidence(self):
        item={'sources':[{'id':'CSPAPERS'}]}
        valid={'verdict':'supported','evidence_ids':['CSPAPERS'],'reason':'Title is present.'}
        self.assertEqual(validate_verdict(item,valid),valid)
        with self.assertRaises(ValueError): validate_verdict(item,{**valid,'evidence_ids':['INVENTED']})
        with self.assertRaises(ValueError): validate_verdict(item,{**valid,'verdict':'verified'})
        self.assertIsNone(wilson(0,0))

    def test_supported_self_citation_and_keynote_are_flagged(self):
        item={'sources':[{'id':'CSPAPERS'},{'id':'EXCLUDED_SESSION'}]}
        verdict={'verdict':'supported','evidence_ids':['CSPAPERS']}
        self.assertEqual(len(evidence_flags(item,verdict)),2)
        self.assertEqual(evidence_flags(item,{'verdict':'conflicting'}),[])
