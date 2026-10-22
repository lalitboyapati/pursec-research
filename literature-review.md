# Literature review: GenAI and statistical methods in usable security

*September 24, 2026 · Focused review of 10 relevant studies*

Existing research establishes two things: statistical reporting problems in usable security predate GenAI, and GenAI is increasingly involved in scientific writing and analysis. **The studies reviewed here do not establish whether GenAI has changed the statistical methods used in usable-security papers.** That is the gap connecting these bodies of work.

## 1. Statistical practices in usable security

### Tang, Bauer, and Christin — SOUPS 2025

[Misuse, Misreporting, Misinterpretation of Statistical Methods in Usable Privacy and Security Papers](https://www.usenix.org/conference/soups2025/presentation/tang)

**The closest prior work.** The authors reviewed 121 papers using null hypothesis significance testing across ten SOUPS editions, covering 2006–2024. In 23% of papers, tests inadequately handled non-independent samples; 58% lacked information needed to check whether an assertion was supported.

The study offers categories for examining statistical use, reporting, and interpretation, including regression. It establishes a strong baseline, but does not investigate GenAI’s influence.

### Ortloff, Tiefenau, and Smith — SOUPS 2023

[SoK: I Have the (Developer) Power!](https://www.usenix.org/conference/soups2023/presentation/ortloff)

The authors examined 54 developer-study papers, extracting information about 467 tests and 413 variables. Many studies were underpowered even to detect large effects—meaning their sample sizes were insufficient to reliably detect those effects.

Their framework connects statistical tests to variables and study design. This shows why counting test names alone provides an incomplete picture. The findings concern developer-centered studies, rather than all usable security.

### Distler et al. — ACM TOCHI 2021

[A Systematic Literature Review of Empirical Methods and Risk Representation in Usable Privacy and Security Research](https://pure.tue.nl/ws/portalfiles/portal/199325689/3469845.pdf)

This review analyzed 284 human-subjects papers from five conferences, published during 2014–2018. It organized study methods, participant characteristics, and approaches to representing security and privacy risks.

It provides context for comparing papers with different designs. Changes in the balance of surveys, experiments, and other studies could explain changes in statistical methods without any GenAI influence. Its focus is broader methodology, not statistical-test selection.

### Thomas Groß — STAST 2019 proceedings, published 2020

[Fidelity of Statistical Reporting in 10 Years of Cyber Security User Studies](https://arxiv.org/abs/2004.06672)

The study examined 1,775 statistical inferences in 114 papers from 2006–2016 using the automated checking tool `statcheck`. Half of the studies reported incomplete results.

This historical evidence makes an important distinction: **missing statistical information is not automatically evidence of incorrect analysis.** It also shows that reporting weaknesses cannot simply be attributed to the arrival of GenAI.

## 2. GenAI in scientific writing and analysis

### Liang et al. — COLM 2024

[Mapping the Increasing Use of LLMs in Scientific Papers](https://openreview.net/pdf?id=YX7QnhxESU)

The authors analyzed 950,965 papers from January 2020 through February 2024 to estimate the prevalence of LLM-modified writing. Estimated usage increased, especially in computer science.

This supports studying scientific change over time, but the estimates concern writing across collections of papers. They do not identify whether an individual researcher used GenAI to choose a statistical method.

### Kobak et al. — Science Advances 2025

[Delving into LLM-assisted writing in biomedical publications through excess vocabulary](https://arxiv.org/abs/2406.07016)

Using more than 15 million biomedical abstracts, the authors identified unusual increases in certain words and estimated a lower bound on LLM-assisted writing.

The study illustrates how changes can be compared against historical trends. However, **changes in language are not evidence of changes in methodology**: researchers may describe the same analysis differently after using a writing assistant.

### Prandner, Wetzelhütter, and Hese — Frontiers in Education, January 2025

[ChatGPT as a data analyst: an exploratory study on AI-supported quantitative data analysis in empirical research](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2024.1417900/full)

The authors explored GPT-3.5 assistance with reproducing statistical analyses, including method selection and code generation. Complex tasks exposed limitations, including repeated unhelpful responses.

This demonstrates a plausible route for GenAI to influence analytical decisions. However, it is an exploratory study of an older model, not evidence of changes across security research. It also highlights that writing assistance, coding assistance, and method selection are distinct uses.

### Dhokotera et al. — International Journal of Public Health 2025

[Generative Artificial Intelligence for Data Analysis: A Randomised Controlled Trial in a Public Health Research Institute](https://www.ssph-journal.org/journals/international-journal-of-public-health/articles/10.3389/ijph.2025.1608572/full)

The trial randomized 31 participants between analysis inside ChatGPT and analysis in R/Stata with ChatGPT support; 30 submitted results. Analysis inside ChatGPT was faster, with no statistically significant difference in task scores.

The study shows that the form of GenAI assistance matters. Both groups used GenAI, so it does not establish whether using GenAI improves analysis compared with working without it. The score result also does not demonstrate equivalent quality.

## 3. Automated extraction from research papers

### Konet et al. — Research Synthesis Methods 2024

[Performance of two large language models for data extraction in evidence synthesis](https://pubmed.ncbi.nlm.nih.gov/38895747/)

Across ten articles, extraction accuracy was 96.3% for Claude 2 and 68.8% for GPT-4 with a PDF plugin. Most errors in the latter setup came from the plugin; accuracy improved when selected text was supplied directly.

The important finding is that **document parsing can determine extraction quality**. These results compare specific setups on a small sample, not the inherent quality of today’s models. They support human validation of extracted evidence.

### Lála et al. — 2023 preprint

[PaperQA: Retrieval-Augmented Generative Agent for Scientific Research](https://arxiv.org/abs/2312.07559)

PaperQA retrieves passages from scientific papers, assesses their relevance, and generates answers grounded in that evidence. The authors also introduce LitQA, a benchmark for literature question answering.

It is a relevant example of an existing research agent. However, success at answering questions does not establish that an agent can exhaustively identify and correctly classify every statistical analysis in a paper.

## What the literature establishes—and leaves open

- **Established:** Usable-security studies had statistical reporting and study-design weaknesses before widespread GenAI adoption.
- **Supported, with limits:** GenAI participates in scientific writing and can assist with analysis. The evidence does not make those two activities interchangeable.
- **Still open in the reviewed work:** Whether statistical methods and their stated justifications changed in usable security around GenAI adoption, beyond existing trends or changes in study types.
- **Key interpretation limit:** A change after 2023 or 2024 would show a temporal association; additional evidence would be needed to attribute it to GenAI.

*Review basis: targeted searches, primary-source abstracts and records, and selected full-text sections. This is a focused literature review, not an exhaustive systematic search or a cover-to-cover assessment of every source. Findings refer to each study’s own sample.*
