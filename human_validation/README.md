# Human validation

Two coders provide the reference standard against which the classifier is evaluated. The
frame is divided between them, so every case is coded once and none is coded twice.

| File | Rows | Composition |
|---|---|---|
| `human_validation_1.html` | 79 | 30 disagreement, 30 agreement, 19 website |
| `human_validation_2.html` | 79 | 30 disagreement, 30 agreement, 19 website |
| `assignment.json` | | which row went to which coder |

## How to code

Open the HTML file in a browser. Nothing is installed and nothing is uploaded; answers stay
in that browser until exported. The file opens on a briefing screen; press **Start coding**.

Read the passage, set the five labels, press **Enter**. AI vocabulary is highlighted so the
relevant sentence is easy to find.

| Key | Label | Set to 1 when the document says… |
|---|---|---|
| **A** | Investment-process AI | the firm uses AI/ML/predictive/algorithmic models in research, security selection, portfolio construction, signal generation, investment risk modelling or trading |
| **B** | Operations / client-service AI | the firm uses AI/ML in non-investment functions: client servicing, chatbots, marketing, compliance, document processing, back office, cybersecurity, meeting notes |
| **C** | AI as a disclosed risk factor | AI is discussed as a *source of risk* — model risk, limits of algorithms, reliance on technology, third-party AI risk, AI-driven cyber risk |
| **D** | Explicit prohibition / non-use | the firm affirmatively states it does **not** use AI, or restricts it |
| **E** | Vendor / product named | a specific AI product or vendor is named. A generic custodian or CRM is **not** label E unless invoked as an AI capability |

Rows are multi-label: a passage can match several, or none.

**Keys:** `A B C D E` toggle · `F` flag for adjudication · `Enter` or `→` next · `←` back ·
`?` rubric. Progress saves automatically; close and resume at any point.

About 43 of the 158 rows contain no AI language at all and are pre-set to zero: one keystroke
each. Some had no keyword hit anywhere in the document; others were pulled in only because
the classifier's keyword filter matches substrings, so `LLM` fires on "insta**llm**ents"
and "enro**llm**ent" and `robo` on "eu**robo**nds". Each such row says so above the
passage. The classifier read the same text and labelled those rows zero too, so there is
nothing to settle. They are in the frame so it remains a probability sample.

## The two rules that settle most hard calls

**Is it AI?** Machine learning, generative AI, large language models, NLP, predictive
analytics, algorithmic or model-driven decisioning, "data science" as a capability — yes. A
CRM, an e-signature tool, a rebalancing rule — no, unless the text itself calls it AI or
predictive.

**Is it this firm?** The label describes the filing firm's own practice. A vendor using AI
inside its product is not the adviser using AI, nor is a third-party manager the adviser
allocates to.

When a row is genuinely ambiguous, record the best answer, press `F`, note why, and move on.

## Rules that protect the result

- Do not discuss any row with the other coder until both files have been exported.
- Do not open `analysis/out/revision/human_validation/*KEY*.csv`. Those hold the model's labels.
- Do not skip rows. The estimator depends on every drawn row being coded.
- Coders are not told which rows are which, and the order differs between the two files.

## When finished

Export the CSV from the browser and place it in this folder, then run:

```
python analysis/a12_two_coder_setup.py score
```

This merges both files into the reference standard and reports classifier sensitivity,
specificity, precision and recall against it, with the website subsample separately.
Disagreement cases enter the frame with probability one and agreement cases with a known
probability below one, so metrics are Horvitz–Thompson weighted to the full classified
sample (Methods 3.5).
