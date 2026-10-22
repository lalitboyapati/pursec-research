from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .core import (Fetcher, RAW, check_pdf, command_proposer, discover_api,
                   discover_repository, download_pdf, enrich, load_reference, norm, now,
                   reconcile, usenix_reference, venue_name, write_json)


def parser():
    p = argparse.ArgumentParser(description='Collect cspapers.org papers and measure evidence-backed coverage.')
    p.add_argument('--venue', required=True, help='cspapers venue, e.g. usenix, sp, ndss, ccs, chi')
    p.add_argument('--year', required=True, type=int)
    p.add_argument('--source', choices=['auto', 'api', 'repository'], default='auto')
    p.add_argument('--reference', type=Path, help='Human-reviewed JSON reference; see examples/reference.schema.json')
    p.add_argument('--official-usenix', action='store_true', help='Build reference from USENIX Security technical sessions')
    p.add_argument('--output', type=Path, default=Path('runs/latest'))
    p.add_argument('--cache', type=Path, default=Path('.cache/pursec'))
    p.add_argument('--delay', type=float, default=0.3)
    p.add_argument('--retries', type=int, default=2)
    p.add_argument('--timeout', type=float, default=30)
    p.add_argument('--abstracts', action='store_true')
    p.add_argument('--enrich', action='store_true', help='Visit official paper pages for authors and PDF URLs')
    p.add_argument('--download-pdfs', action='store_true', help='Requires pypdf; title-match readable PDFs before accepting')
    p.add_argument('--limit-enrichment', type=int, help='Bound paper page/PDF/abstract requests for smoke testing')
    p.add_argument('--proposer-command', action='append', default=[],
                   help='Optional LLM adapter command; repeat for independent proposers (JSON stdin/stdout)')
    p.add_argument('--proposer-rounds', type=int, default=2)
    p.add_argument('--proposer-timeout', type=float, default=600)
    p.add_argument('--recover-missing', action='store_true',
                   help='Add missing official records separately; never count them as cspapers discoveries')
    return p


def run(args):
    if not 1960 <= args.year <= 2100:
        raise ValueError('Year must be between 1960 and 2100')
    if args.delay < 0 or args.retries < 0 or args.timeout <= 0 or args.proposer_rounds < 1 or args.proposer_timeout <= 0:
        raise ValueError('Invalid delay, retry, timeout, or round setting')
    if args.limit_enrichment is not None and args.limit_enrichment < 0:
        raise ValueError('Enrichment limit must be nonnegative')
    if args.reference and args.official_usenix:
        raise ValueError('Choose either --reference or --official-usenix')
    venue = venue_name(args.venue)
    if not venue.isalnum():
        raise ValueError('Venue must be an alphanumeric cspapers identifier')
    if args.official_usenix and venue != 'usenix':
        raise ValueError('--official-usenix supports USENIX Security only')
    if args.download_pdfs:
        try:
            import pypdf  # noqa: F401
        except ImportError as exc:
            raise ValueError('Install pypdf before downloading PDFs: pip install -e .') from exc
    args.output.mkdir(parents=True, exist_ok=True)
    # Require a clean output directory so old PDFs cannot appear to belong to a new run.
    if any(args.output.iterdir()):
        raise ValueError('Output directory is not empty; choose a new --output path')
    fetch = Fetcher(args.cache, args.delay, args.retries, args.timeout)
    warnings, comparisons, agent_log = [], [], []
    try:
        print(f'Discovering {venue} {args.year} from cspapers.org...', flush=True)
        if args.source == 'repository':
            rows, discovery = discover_repository(fetch, venue, args.year)
        elif args.source == 'api':
            rows, discovery = discover_api(fetch, venue, args.year)
        else:
            try:
                rows, discovery = discover_api(fetch, venue, args.year)
            except Exception as exc:
                warnings.append(f'API unavailable or incomplete; repository fallback: {exc}')
                print('API unavailable/incomplete; using cspapers public repository.', flush=True)
                rows, discovery = discover_repository(fetch, venue, args.year)
        write_json(args.output / 'discovered.json', rows)
        reference = None
        if args.reference:
            reference = load_reference(args.reference, venue, args.year)
        elif args.official_usenix:
            reference = usenix_reference(fetch, args.year)
            write_json(args.output / 'reference.json', reference)
            # Apply the same validation to scraped and supplied references.
            reference = load_reference(args.output / 'reference.json', venue, args.year)
            warnings.append('Official reference was automatically extracted; review eligibility and omissions before publication.')
        if reference:
            write_json(args.output / 'reference.json', reference)
        baseline, _, baseline_missing = reconcile(rows, reference)
        comparisons.append({'setup': 'direct_cspapers', 'unique_records': len(baseline),
                            'reference_matches': sum(r['verification'] == 'title_venue_year_matched' for r in baseline),
                            'missing': len(baseline_missing) if reference else None})
        selected = rows
        if args.proposer_command:
            selected = []
            # Each proposer sees the same source evidence, never another proposer's output.
            # This evaluates selection/extraction, not independent web search.
            for number, command in enumerate(args.proposer_command, 1):
                feedback, accumulated = [], []
                for round_no in range(1, args.proposer_rounds + 1):
                    proposed, rejected = command_proposer(command, rows, venue, args.year, feedback, args.proposer_timeout)
                    accumulated.extend(proposed)
                    covered = {norm(r['title']) for r in accumulated}
                    feedback = rejected + [{'title': r['title'], 'reason': 'Source record omitted'}
                                           for r in rows if norm(r['title']) not in covered]
                    agent_log.append({'agent': number, 'round': round_no, 'proposals': proposed,
                                      'rejected': rejected, 'feedback': feedback})
                    if not feedback:
                        break
                checked, _, missing = reconcile(accumulated, reference)
                comparisons.append({'setup': f'proposer_{number}', 'unique_records': len(checked),
                                    'reference_matches': sum(r['verification'] == 'title_venue_year_matched' for r in checked),
                                    'missing': len(missing) if reference else None})
                selected.extend(accumulated)
        records, duplicates, missing = reconcile(selected, reference)
        discovery_matches = sum(r['verification'] == 'title_venue_year_matched' for r in records)
        write_json(args.output / 'missing-from-discovery.json', missing)
        if args.recover_missing and reference:
            for m in missing:
                recovered, _, _ = reconcile([m], reference)
                recovered[0]['origin'] = 'official_reference_recovery'
                records.extend(recovered)
        for r in records:
            r.setdefault('origin', 'cspapers')
        for i, record in enumerate(records):
            if args.limit_enrichment is not None and i >= args.limit_enrichment:
                break
            if args.abstracts and record.get('index'):
                try:
                    url = record['source_url']
                    if discovery['source'] == 'cspapers_api':
                        from urllib.parse import quote
                        path = record['index']
                        if not path.startswith(('index/', 'index2/')) or '..' in path.split('/'):
                            raise ValueError('Invalid abstract index path')
                        url = f'{RAW}/main/{quote(path, safe="/")}'
                    record['abstract'] = fetch.get(url).decode('utf-8')
                    record['abstract_status'] = 'present' if record['abstract'].strip() else 'missing'
                except Exception as exc:
                    record['abstract_status'] = 'error'; record['feedback'].append(str(exc))
            if args.enrich or args.download_pdfs:
                try:
                    enrich(fetch, record)
                    if args.download_pdfs:
                        download_pdf(fetch, record, args.output)
                except Exception as exc:
                    record['feedback'].append(str(exc))
                    if args.download_pdfs:
                        record['pdf_status'] = 'error'
                    else:
                        record['enrichment_status'] = 'error'
        total = len(reference['papers']) if reference else None
        matched = sum(r['verification'] == 'title_venue_year_matched' for r in records)
        pdfs = sum(r['pdf_status'] == 'title_matched' for r in records)
        report = {'started_scope': {'venue': venue, 'year': args.year}, 'finished_at': now(),
                  'discovery': discovery, 'source_records': len(rows), 'selected_unique_records': len(records),
                  'duplicate_records': len(duplicates), 'expected_papers': total,
                  'reference_human_reviewed': reference.get('human_reviewed', False) if reference else False,
                  'reference_matches_from_discovery': discovery_matches,
                  'discovery_coverage': discovery_matches / total if total else None,
                  'collection_reference_matches': matched,
                  'collection_coverage': matched / total if total else None,
                  'reference_match_rate': matched / len(records) if records and reference else None,
                  'pdf_title_matches': pdfs, 'pdf_coverage': pdfs / total if total and args.download_pdfs else None,
                  'missing_from_discovery': len(missing) if reference else None,
                  'unresolved_records': sum(bool(r['feedback']) or r['verification'] != 'title_venue_year_matched' for r in records),
                  'warnings': warnings, 'comparisons': comparisons,
                  'configuration': {'source': args.source, 'abstracts': args.abstracts,
                    'enrich': args.enrich, 'download_pdfs': args.download_pdfs,
                    'limit_enrichment': args.limit_enrichment, 'proposer_count': len(args.proposer_command),
                    'proposer_rounds': args.proposer_rounds, 'recover_missing': args.recover_missing},
                  'interpretation': 'Coverage is relative to the supplied/extracted reference, not proven conference completeness. '
                                    'Title/venue/year matches do not independently validate authors or the final publication version. '
                                    'Null means unmeasured, not zero. LLM agreement is not ground truth.'}
        write_json(args.output / 'papers.json', records)
        write_json(args.output / 'duplicates.json', duplicates)
        write_json(args.output / 'agent-log.json', agent_log)
        write_json(args.output / 'report.json', report)
        with (args.output / 'papers.csv').open('w', newline='') as file:
            fields = ['title', 'official_title', 'venue', 'year', 'authors', 'source_url', 'official_url',
                      'verification', 'authors_status', 'pdf_url', 'pdf_status', 'origin']
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore'); writer.writeheader()
            for r in records:
                writer.writerow({**r, 'authors': '; '.join(r['authors'])})
        coverage = f'{discovery_matches}/{total} ({discovery_matches / total:.1%})' if total else 'Not measured (no reference)'
        (args.output / 'report.md').write_text(
            f'# Collection report: {venue.upper()} {args.year}\n\n'
            f'- Source: {discovery["source"]}\n- cspapers records: {len(rows)}\n'
            f'- Discovery coverage against reference: {coverage}\n'
            f'- Downloaded PDFs with matching title: {pdfs}\n'
            f'- Reference human-reviewed: {report["reference_human_reviewed"]}\n\n'
            f'{report["interpretation"]}\n\n' + '\n'.join(f'- {w}' for w in warnings) + '\n')
        print(json.dumps(report, indent=2))
        return report
    except Exception as exc:
        write_json(args.output / 'failure.json', {'error': str(exc), 'at': now()})
        raise
    finally:
        write_json(args.output / 'requests.json', fetch.events)


def main():
    args = parser().parse_args()
    try:
        run(args)
    except Exception as exc:
        print(f'Collection failed: {exc}', file=sys.stderr)
        return 1
    return 0
