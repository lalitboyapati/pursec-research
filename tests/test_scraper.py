import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from pursec_scraper.core import (Page, candidate, check_pdf, command_proposer,
    discover_api, discover_repository, enrich, load_reference, norm, reconcile, tree, usenix_reference)
from pursec_scraper.cli import parser, run


class QueueFetch:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.urls = []

    def json(self, url):
        self.urls.append(url)
        return next(self.pages)

    def get(self, url):
        self.urls.append(url)
        return next(self.pages).encode()


def row(title='Paper A', year=2024, venue='usenix'):
    return candidate(title, venue, year, 'https://example.org/' + title.replace(' ', '-'))


def ref():
    return {'venue': 'usenix', 'year': 2024, 'source_url': 'https://official.org',
            'papers': [row('Paper A'), row('Paper B')]}


class ScraperTests(unittest.TestCase):
    def test_pagination_uses_actual_offset(self):
        f = QueueFetch([{'total': 2, 'data': [row('A')]}, {'total': 2, 'data': [row('B')]}])
        rows, _ = discover_api(f, 'usenix', 2024)
        self.assertEqual(len(rows), 2)
        self.assertEqual(parse_qs(urlparse(f.urls[1]).query)['skip'], ['1'])

    def test_repeated_page_fails(self):
        f = QueueFetch([{'total': 2, 'data': [row()]}, {'total': 2, 'data': [row()]}])
        with self.assertRaisesRegex(ValueError, 'repeated'):
            discover_api(f, 'usenix', 2024)

    def test_early_empty_page_fails(self):
        f = QueueFetch([{'total': 2, 'data': [row()]}, {'total': 2, 'data': []}])
        with self.assertRaisesRegex(ValueError, 'ended'):
            discover_api(f, 'usenix', 2024)

    def test_wrong_year_not_accepted(self):
        with self.assertRaisesRegex(ValueError, 'out-of-scope'):
            discover_api(QueueFetch([{'total': 1, 'data': [row(year=2023)]}]), 'usenix', 2024)

    def test_changing_total_fails(self):
        with self.assertRaisesRegex(ValueError, 'changed'):
            discover_api(QueueFetch([{'total': 2, 'data': [row()]}, {'total': 3, 'data': []}]), 'usenix', 2024)

    def test_zero_results(self):
        rows, info = discover_api(QueueFetch([{'total': 0, 'data': []}]), 'usenix', 2024)
        self.assertEqual(rows, [])
        self.assertEqual(info['reported_total'], 0)

    def test_truncated_tree_rejected(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            tree(QueueFetch([{'truncated': True, 'tree': []}]), 'abc')

    def test_repository_pinned_and_not_contents_capped(self):
        pages = [{'sha': 'commit123'}]
        for name in ['index2', '2024', 'usenix']:
            pages.append({'tree': [{'path': name, 'type': 'tree', 'sha': name}], 'truncated': False})
        pages.append({'tree': [{'path': f'Paper {i}', 'type': 'blob'} for i in range(1005)]})
        rows, meta = discover_repository(QueueFetch(pages), 'usenix', 2024)
        self.assertEqual(len(rows), 1005)
        self.assertIn('/commit123/', rows[0]['source_url'])

    def test_duplicate_does_not_inflate_coverage(self):
        records, duplicates, missing = reconcile([row(), row()], ref())
        self.assertEqual((len(records), len(duplicates), len(missing)), (1, 1, 1))

    def test_wrong_year_unresolved(self):
        records, _, missing = reconcile([row(year=2023)], ref())
        self.assertEqual(records[0]['verification'], 'needs_review')
        self.assertEqual(len(missing), 2)

    def test_title_variation_and_similar_title(self):
        records, _, missing = reconcile([row('Paper A.'), row('Paper AB')], ref())
        self.assertEqual(records[0]['verification'], 'title_venue_year_matched')
        self.assertEqual(records[1]['verification'], 'needs_review')
        self.assertEqual(len(missing), 1)

    def test_no_reference_is_unverified(self):
        records, _, _ = reconcile([row()], None)
        self.assertEqual(records[0]['verification'], 'unverified')

    def test_reference_wrong_scope_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'ref.json'
            data = ref(); p.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_reference(p, 'ccs', 2024)
            data['papers'].append(row()); p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'duplicate'): load_reference(p, 'usenix', 2024)

    def test_official_list_rejects_foreign_and_other_year_links(self):
        html = ('<a href="/conference/usenixsecurity24/presentation/a">Paper <em>A</em></a>'
                '<a href="https://evil.org/conference/usenixsecurity24/presentation/b">B</a>'
                '<a href="/conference/usenixsecurity23/presentation/c">C</a>')
        result = usenix_reference(QueueFetch([html]), 2024)
        self.assertEqual([p['title'] for p in result['papers']], ['Paper A'])

    def test_publisher_title_mismatch_blocks_enrichment(self):
        record = row(); record['official_url'] = 'https://official.org/a'
        with self.assertRaisesRegex(ValueError, 'title'):
            enrich(QueueFetch(['<meta name="citation_title" content="Different Paper">']), record)
        self.assertEqual(record['authors'], [])

    def test_hallucinated_proposal_rejected(self):
        output = {'papers': [{'title': 'Made up', 'source_url': row()['source_url']},
                             {'title': 'Paper A', 'source_url': row()['source_url']}]}
        with patch('pursec_scraper.core.subprocess.run') as mock:
            mock.return_value.stdout = json.dumps(output)
            accepted, rejected = command_proposer('model-adapter', [row()], 'usenix', 2024, [])
        self.assertEqual((len(accepted), len(rejected)), (1, 1))
        self.assertFalse(mock.call_args.kwargs.get('shell', False))

    def test_html_disguised_as_pdf(self):
        self.assertEqual(check_pdf(b'<html>Blocked</html>', 'Paper A')[0], 'invalid_pdf')

    def test_pdf_wrong_title_and_matching_title(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        except ImportError:
            self.skipTest('pypdf optional dependency not installed')
        writer = PdfWriter(); page = writer.add_blank_page(600, 800)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject(); stream.set_data(b'BT /F1 14 Tf 50 700 Td (Paper A) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        buf = io.BytesIO(); writer.write(buf)
        self.assertEqual(check_pdf(buf.getvalue(), 'Paper A')[0], 'title_matched')
        self.assertEqual(check_pdf(buf.getvalue(), 'Paper B')[0], 'needs_review')

    def test_cli_report_keeps_unknown_coverage_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = parser().parse_args(['--venue', 'usenix', '--year', '2024', '--source', 'repository',
                                       '--output', tmp + '/output', '--cache', tmp + '/cache'])
            with patch('pursec_scraper.cli.discover_repository', return_value=([row()], {'source':'test'})):
                report = run(args)
            self.assertIsNone(report['discovery_coverage'])
            self.assertEqual(report['unresolved_records'], 1)
            self.assertTrue((Path(tmp) / 'output' / 'papers.csv').exists())

    def test_official_recovery_does_not_inflate_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'ref.json'; p.write_text(json.dumps(ref()))
            args = parser().parse_args(['--venue','usenix','--year','2024','--source','repository',
                '--reference',str(p),'--recover-missing','--output',tmp+'/out','--cache',tmp+'/cache'])
            with patch('pursec_scraper.cli.discover_repository', return_value=([row()], {'source':'test'})):
                report = run(args)
            self.assertEqual(report['discovery_coverage'], .5)
            self.assertEqual(report['collection_coverage'], 1.)

class AdditionalTests(unittest.TestCase):
    def test_keynote_excluded_and_logged(self):
        html = ('<article class="node-session"><h2>Keynote Address</h2>'
                '<article class="node-paper"><h2><a href="/conference/usenixsecurity24/presentation/keynote">Talk</a></h2></article></article>'
                '<article class="node-session"><h2>Privacy</h2><article class="node-paper">'
                '<h2><a href="/conference/usenixsecurity24/presentation/a">Paper A</a></h2></article></article>')
        result = usenix_reference(QueueFetch([html]), 2024)
        self.assertEqual([r['title'] for r in result['papers']], ['Paper A'])
        self.assertEqual(len(result['excluded_presentations']), 1)

    def test_same_search_url_keeps_multiple_model_records(self):
        rows = [row('A'), row('B')]
        for r in rows: r['source_url'] = 'https://api.cspapers.org/'
        with patch('pursec_scraper.core.subprocess.run') as mock:
            mock.return_value.stdout = json.dumps({'papers': rows + [{'title': 123, 'source_url': 'x'}]})
            accepted, rejected = command_proposer('adapter', rows, 'usenix', 2024, [])
        self.assertEqual(len(accepted), 2)
        self.assertEqual(len(rejected), 1)

    def test_two_proposer_feedback_and_combination(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'ref.json'; p.write_text(json.dumps(ref()))
            args = parser().parse_args(['--venue','usenix','--year','2024','--source','repository',
                '--reference',str(p),'--output',tmp+'/out','--cache',tmp+'/cache',
                '--proposer-command','first','--proposer-command','second'])
            def model(command, rows, venue, year, feedback, timeout):
                return ([rows[0]] if command == 'first' and not feedback else rows), []
            with patch('pursec_scraper.cli.discover_repository', return_value=([row(), row('Paper B')], {'source':'test'})), \
                 patch('pursec_scraper.cli.command_proposer', side_effect=model):
                report = run(args)
            log = json.loads((Path(tmp)/'out/agent-log.json').read_text())
            self.assertEqual(len(log), 3)
            self.assertEqual(report['discovery_coverage'], 1)
            self.assertEqual(len(report['comparisons']), 3)
            self.assertEqual(report['selected_unique_records'], 2)
            self.assertIsNone(report['pdf_coverage'])

    def test_ollama_adapter_contract(self):
        from pursec_scraper.ollama_proposer import propose
        response = io.BytesIO(json.dumps({'message': {'content': json.dumps({'papers': [row()]})}}).encode())
        with patch('pursec_scraper.ollama_proposer.urlopen', return_value=response) as mocked:
            result = propose({'evidence':[row()], 'venue':'usenix','year':2024}, 'test-model')
        self.assertEqual(len(result['papers']), 1)
        request = json.loads(mocked.call_args.args[0].data)
        self.assertFalse(request['stream'])
        self.assertEqual(request['model'], 'test-model')


if __name__ == '__main__':
    unittest.main()
