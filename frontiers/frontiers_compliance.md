# Frontiers in Artificial Intelligence — Original Research: compliance checklist

Manuscript: *AI Use and Risk Disclosure by Investment Advisers* (`manuscript.tex`). **Status legend:** ✅ done · ⚠️ needs your input · ➖ N/A.
Every requirement from the Frontiers author guidelines + the official LaTeX template is mapped below.

| # | Requirement (Frontiers spec) | Our status | Where / note |
|---|---|---|---|
| 1 | Use Frontiers template; LaTeX submit `.tex`+`.pdf`+`.bib`+figures | ✅ | `FrontiersinHarvard.cls`; all files delivered in `submission/` |
| 2 | **Reference style = Harvard (author-date)** for Frontiers in AI | ✅ | `\bibliographystyle{Frontiers-Harvard}`, `\citep/\citet` |
| 3 | Title: concise, states main result, no abbreviations, includes keywords | ✅ | Title names the finding ("AI Use and Risk Disclosure …  Disclosure"), no abbreviations |
| 4 | Running title | ✅ | `\title[AI Use and Risk Disclosure]{…}` |
| 5 | Author names listed; corresponding author marked `*` | ✅ | `Samir Chincholikar$^{1}$, Robin Chawla$^{2,*}$` |
| 6 | Affiliation format: Dept, Org, City, State (US/CA/AU), Country — no street/zip | ✅ | $^{1}$Independent Researcher, New York, NY, United States; $^{2}$Independent Researcher, New York, NY, United States — **confirm/adjust if needed** |
| 7 | Corresponding email in correspondence block | ✅ | robin.chawla.cse14@iitbhu.ac.in |
| 8 | Abstract: one paragraph, IMRAD-style, **no citations/figures/tables** | ✅ | Single paragraph; zero citations; policy names mentioned without author-date cites |
| 9 | Abstract SEO: keywords in first two sentences | ✅ | "artificial intelligence", "investment advisers", "fiduciary disclosures" up front |
| 10 | Keywords: **5–8** | ✅ | 8 keywords provided |
| 11 | Section structure: Introduction (no subheadings), Materials & Methods, Results, Discussion | ✅ | Introduction has no subheadings; Materials and methods / Results / Discussion present; Conclusion as a Discussion subsection |
| 12 | Materials & Methods placement (before/after Results) | ✅ | Before Results (permitted) |
| 13 | **Single/1.5 spacing + page numbers + line numbers** | ✅ | Template `onehalfspacing` (Frontiers LaTeX default) + `\linenumbers` + page numbers |
| 14 | American English default | ✅ | US spelling throughout |
| 15 | Abbreviations defined at first use; kept minimal | ✅ | AI, RIA, AUM, IAPD, SEC, PABAK defined on first use |
| 16 | References: peer-reviewed, up-to-date; citation↔list complete | ✅ | 37 refs, 3 literature streams; all `\citep` resolve (0 undefined at compile) |
| 17 | Reference list: first 6 authors + et al., initials, DOI when available | ✅ | `.bst` enforces; DOIs to be added to journal refs where available |
| 18 | Only published/accepted works; preprints need DOI/URL + labeled | ✅ | Preprints (arXiv:2108.07258, arXiv:2304.06588) labeled; legal/policy sources as `@techreport` |
| 19 | **Figures + tables ≤ 15 combined** (Original Research) | ✅ | **4 figures + 6 tables = 10** |
| 20 | Figures cited in numerical order; mentioned in text | ✅ | Fig 1→4 cited in order (`\ref{fig:typology}` … `fig:venue`) |
| 21 | Figure captions at END of manuscript; panels bold `(A)` | ✅ | All figures + captions after references; figures are single-panel |
| 22 | Figures: 300 dpi, RGB, ≥8pt text, ≥2pt lines, 85/180mm width | ✅ | Generated at 300 dpi, colorblind-safe (blue/orange + hatching), single/double-column widths |
| 23 | Alt text for figures | ⚠️ | Provide on the submission portal (captions are descriptive; alt-text field is portal-side) |
| 24 | Tables **built in LaTeX**, at END, caption immediately BEFORE table | ✅ | 6 `\begin{table}` in LaTeX after references; `\caption` before `\begin{tabular}` |
| 25 | Tables cited in numerical order | ✅ | Tables 1→6 cited in order |
| 26 | **Conflict of Interest** statement | ✅ | Present (none) |
| 27 | **Author Contributions** (CRediT, initials) | ✅ | "SC: …; RC: …" |
| 28 | **Funding** statement | ✅ | "financial support was not received" |
| 29 | **Acknowledgments** | ✅ | Present (SEC public systems + reproducibility deposit) |
| 30 | **Data Availability Statement** naming repository + link | ⚠️ | GitHub link included; **insert Zenodo + Code Ocean DOIs on release** |
| 31 | **Ethics statement** | ✅ | No human/animal subjects; public entity filings only |
| 32 | **Generative AI statement** with name/version/model/source; AI not an author | ✅ | Dedicated section + §3.4 Methods: gpt-4o / gpt-4o-mini (classification) and Anthropic Claude (validation + drafting); no AI author |
| 33 | Verbatim text in quotes with source | ✅ | Quoted enforcement language attributed to SEC releases IA-6573/IA-6574 |
| 34 | Inclusive language / SAGER | ✅ | No sex/gender claims; neutral language |
| 35 | Word count + #figures/#tables on first page | ⚠️ | Body ≈ 6,300 words; 4 figures, 6 tables — add on the portal's first-page field if required |
| 36 | Supplementary material: S1 (exposure adjudication), S2 (validation), + prompts/logs | ✅ | S1/S2 + coding sheets and capsule available as the reproducibility artifact/Supplementary |
| 37 | Registration of submitting author on Frontiers | ⚠️ | Portal step (yours) |

## Items requiring your input before submission (3)
1. **Affiliation** — the block reads "Independent Researcher, New York, NY, United States" for both authors (matching your Paper 13 submission); confirm or adjust to your preferred wording.
2. **Zenodo + Code Ocean DOIs** — insert into the Data Availability Statement (and `CITATION.cff`, `.zenodo.json`) once you mint the release; the GitHub link is already in place.
3. **Portal steps** — per-figure alt text, corresponding-author registration, and (if requested) the words/figures/tables count field.

## Verified at compile
`pdflatex → bibtex → pdflatex×2` compiles with **0 errors**, **0 undefined citations**, 37 references formatted in Harvard style, line + page numbers present, 18 pages. Files to upload: `manuscript.tex`, `references.bib`, `manuscript.pdf`, `figures/fig1–4.png` (individual copies in `submission/Figure1–4.png`), and the class/style files (`FrontiersinHarvard.cls`, `Frontiers-Harvard.bst`, logos) if the portal compiles.
