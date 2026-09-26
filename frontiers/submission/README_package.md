# Revision package — AI Use and Risk Disclosure by Investment Advisers

*Frontiers in Artificial Intelligence · Original Research · AI in Finance*
*Revision in response to Reviewer 1 and Reviewer 3.*

| File | What it is |
|---|---|
| `../manuscript.pdf` | **The revised manuscript.** 20 pp. This is the paper. |
| `manuscript_v1_as_submitted.pdf` | The manuscript exactly as first submitted, taken from the commit sent to the journal. |
| `manuscript_tracked.pdf` | v1 against the current manuscript, latexdiff. 30 pp. |
| `response_reviewer_1.pdf` | Point-by-point response to Reviewer 1, 7 points, 4 pp. This is the file to upload. |
| `response_reviewer_1.txt` | The same letter as plain text. It is the source the PDF is typeset from. |
| `response_reviewer_3.pdf` | Point-by-point response to Reviewer 3, 9 points, 4 pp. This is the file to upload. |
| `response_reviewer_3.txt` | The same letter as plain text. |
| `r1_portal.txt` | Reviewer 1 response compressed to the portal's 4,000-character field. |
| `r3_portal.txt` | Reviewer 3 response compressed to the portal's 4,000-character field. |
| `Figure1.png`, `Figure2.png` | The two figures as individual files, numbered as in the compiled PDF. |

Both response letters cite the **printed margin line numbers** of `../manuscript.pdf`, not
`.tex` source lines. All 73 page-and-line references were machine-verified against the compiled
PDF: every cited line exists, sits on the page claimed, and contains the content the letter
attributes to it. Re-verify after any edit to the manuscript, because pagination and line
numbering move.

`manuscript_v1_as_submitted.tex` and `references_v1_as_submitted.bib` are the frozen v1 sources,
kept so the tracked-changes PDF stays reproducible now that the revision has been promoted over
`frontiers/manuscript.tex`.

## Rebuilding

```
bash ../build_package.sh            # rebuild manuscript, figures, tracked changes, cover letter, DOCX
bash ../build_package.sh --check    # report what is stale, exit 1 if anything is
```

`build_responses.py` typesets the two response PDFs from the `.txt` letters. They carry no
bold, italics or rules; the structure is spacing and bullets only. Edit the `.txt` file, never
the generated `.tex`.

`build_tracked.sh` regenerates `manuscript_tracked.pdf` alone. It builds in a temp directory and
leaves nothing behind.

## Outstanding

The human coding is not final. Every human-verification figure in the manuscript and in the
response letters currently comes from a test pass, and the three
`capsule/data/human_verification/` files the Data Availability Statement names are not yet
written. `python analysis/a12_two_coder_setup.py score` produces them from the two coder exports
and fills `analysis/out/revision/human_validation/validation_results.json`. Until then
the repository's `reproduce.sh` stage 4 exits non-zero and says so.
