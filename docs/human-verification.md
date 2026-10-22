# Verify the collection yourself

The current run contains **420 unique title records**, with author/abstract/PDF enrichment tested on **three** records. This is an audit of collection reliability, not a review of the papers' scientific results.

## 1. Open the audit in VS Code

From the project folder:

```bash
source .venv/bin/activate
code runs/usenix-2024-review/human-review.json
```

If `code` is unavailable, use VS Code → File → Open File. The audit has 37 records: 30 reproducibly random matched records, four unmatched records, and three PDF examples. Keep IDs and `selection` unchanged. Do your first pass before reading `llm-review.json` to avoid adopting the model's answers.

## 2. Check each record against original sources

Open its `cspapers_url` and the relevant link in `official_candidates`. For unmatched titles, these are **suggestions**, not verified identities. Search the official conference list when none matches.

Edit the `decisions` fields:

| Field | What to check |
|---|---|
| `membership` | Is this an eligible research paper at USENIX Security 2024, rather than a keynote or another kind of session? |
| `title` | Does the collected title agree with the official title? Explain shortened titles or notation differences. |
| `year_venue` | Do both year and conference agree with the official record? |
| `authors` | If collected, compare the complete author list with the official paper. |
| `pdf` | If downloaded, open `pdf_path`; check title, authors, conference/year, and that it is the intended full paper. |

Use `correct`, `incorrect`, or `uncertain`. Keep `pending` for unfinished work and `not_collected` for unavailable fields. Missing author/PDF data is not a successful verification. Add your name, date, source-based notes, and proposed correction. Do not silently change the original scraped data.

Example of an edited record fragment (illustrative, not an actual judgment):

```json
{
  "decisions": {
    "membership": "correct",
    "title": "incorrect",
    "year_venue": "correct",
    "authors": "not_collected",
    "pdf": "not_collected"
  },
  "reviewer": "Lalit",
  "checked_at": "2026-10-22",
  "notes": "Compared with the linked official presentation; the collected title omits its final word.",
  "correction": "Record the exact official title here."
}
```

## 3. Check completeness separately

Open `runs/usenix-2024-review/reference-review.json`. Follow `official_list_url` and compare the full official list against `runs/usenix-2024-validated/reference.json`. Check excluded sessions and the one unmatched reference title. Mark `reference_complete` and `exclusions_correct` as `correct`, `incorrect`, or `uncertain`; add reviewer and notes.

A title variant can appear as both an unmatched discovery and a missing reference. Resolve identity before claiming a paper was actually missed. Also inspect `duplicates.json` for incorrect merges if conducting a full collection audit.

## 4. Calculate your results

```bash
python -m pursec_scraper.review summarize
```

Results go to `runs/usenix-2024-review/summary.json`. It reports field-level counts and LLM outcomes separately. Once all 30 random membership decisions are correct/incorrect, it calculates membership accuracy within the automatically matched group and an approximate 95% Wilson interval. Uncertain or unfinished judgments leave that estimate unset. The seven targeted cases do not inflate the random-sample estimate.

Even 30/30 correct would be approximately **88.6–100%** on that interval, not proof of perfect accuracy. This small audit is a useful pilot; it does not estimate accuracy of all 420 records, author lists, or PDFs. Three deliberately selected PDF examples test functionality, not population-level PDF accuracy.

Then compare your judgments with `llm-review.json`: note disagreements and whether each model claim actually follows from its cited evidence. LLM agreement is not ground truth.

## Next work

1. Complete this audit and resolve the four unmatched discoveries and one reference mismatch.
2. Record reviewed corrections separately, then rerun the pipeline to measure their effect.
3. Validate another conference-year held out from development. Compare proposer models on the same inputs and human labels if studying agent performance.
4. Expand abstract/PDF collection, then define usable-security eligibility labels with the team. Statistical-method extraction comes after reliable collection.

For a new run, create a new review directory:

```bash
python -m pursec_scraper.review prepare --run runs/YOUR-RUN --output runs/YOUR-AUDIT --sample-size 30 --seed 20261022
python -m pursec_scraper.review llm --output runs/YOUR-AUDIT --model llama3.2:latest
python -m pursec_scraper.review summarize --output runs/YOUR-AUDIT
```

The LLM command requires that model already installed and Ollama running locally. It reviews saved evidence only, has no independent browsing, saves raw responses, and resumes successful items without overwriting human decisions.
