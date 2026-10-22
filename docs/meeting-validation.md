# This week's research deliverable

**Built a working cspapers collection pipeline and a reproducible audit workflow.** Pilot: USENIX Security 2024. This is a collection/reliability milestone; it does not yet measure changes in statistical methods or the effect of GenAI.

## Measured results

| Measure | Result |
|---|---:|
| Source records collected | 430 |
| Duplicate rows removed | 10 |
| Unique title records | 420 |
| Automatically extracted official research-paper reference | 417 |
| Discovered titles matched to reference | 416 |
| Coverage relative to that reference | 99.76% |
| Collected titles requiring resolution | 4 |
| Reference titles not exactly matched | 1 |
| Author/abstract/PDF enrichment smoke test | 3 records |
| Readable, title-matched PDFs downloaded | 3 |
| Automated tests passing | 30 |
| Human-reviewed records | 0 — audit prepared, pending |

Snapshot: cspapers repository commit `92397bd6e2418b494f37b1c102c6706050b70480`. Live run used the site's public dataset, not its unavailable API. Collection date: October 22, 2026. Counts come from `runs/usenix-2024-validated/report.json`; the committed [measurement snapshot](validation-summary.json) preserves them.

Coverage depends on the reference list being correct and complete. It is not a precision score. Only three records have enriched fields; the 420 figure is a title-record count, not a full-text corpus.

## Actual LLM pre-review

Ran the installed local **llama3.2:latest** on 37 records: 30 seeded random matches, all four unmatched discoveries, and all three downloaded PDFs. The two targeted groups were outside the random sample. Evidence consisted of collected source snippets, candidate official reference entries, and publisher/PDF text where collected. The model had no independent browser access.

- **First pass:** 37/37 rejected because the model cited record IDs instead of evidence IDs. Raw output retained locally as `llm-review-initial-rejected.json`.
- **Second pass:** constrained JSON schema produced 37/37 valid responses. The model called all 37 “supported.”
- **Evidence checks flagged 17/37** because they cited only cspapers. This includes a keynote with explicit exclusion evidence. Its “supported” label is therefore unreliable.
- The other 20 responses are **not proven correct**; valid citations do not establish that the reasoning follows from them.

**Finding: this small local model should not act as an acceptance gate.** The experiment demonstrates why source cross-checking and human review are necessary. No LLM verdict changed the dataset or prefilled a human decision. [Saved model judgments](llm-pre-review.json) make this result inspectable. This is one model run after a format correction, not a benchmark of multiple independent agents.

## Cases to resolve

| Collected title | Evidence or question |
|---|---|
| A World Where We Trust Hard-Won Lessons in Security Research, Technology, and People | Official extraction identifies an excluded keynote; inspect scope and remove from research-paper set if confirmed. |
| Closed-Form Bounds for DP-SGD against Record-level Inference | Official reference adds “Attacks”; confirm identity before treating this as a missing paper. |
| Prefetch for Fun and Profit: A Revisit of Prefetch Attacks on Apple M1 | Unmatched; investigate the correct venue/year and publication record. |
| pi-Jack: Physical-World Adversarial Attack on Monocular Depth Estimation with Perspective Hijacking | Inspect notation against the separately collected “π-Jack” record; confirm whether this is a duplicate. |

These are review leads, not completed human judgments. Reference misses and unmatched discoveries may describe the same underlying paper.

## What to do before the meeting

Follow the [human-verification guide](human-verification.md). Check the 37 records and official reference scope, then run `python -m pursec_scraper.review summarize`. Report unresolved cases honestly. The random sample yields a membership-accuracy estimate only after all 30 membership decisions are resolved; targeted cases are reported separately.

Suggested meeting wording:

> I built the collector and tested it on USENIX Security 2024. It collected 430 source rows and produced 420 unique title records, matching 416 of 417 entries in the extracted official reference. I also tested downloading and checking three PDFs. I prepared a reproducible 37-record human audit and tested local LLM pre-review; the model failed evidence checks on 17 cases, so I am keeping source verification and human review as the basis for reliability. Next I will resolve mismatches and validate another conference-year before scaling up.
