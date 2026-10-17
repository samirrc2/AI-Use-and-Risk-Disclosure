# What does this research answer?

**Published article:** Chincholikar, S., and Chawla, R. (2026). *AI use and risk disclosure by investment advisers*. *Frontiers in Artificial Intelligence*.

**Read the peer-reviewed article:** https://doi.org/10.3389/frai.2026.1969257

This guide summarizes the questions investigated in the study and the limits of its findings. The study examines **disclosures** in US investment advisers' public Form ADV Part 2A brochures, not all AI systems that advisers may use in practice.

## What evidence does the study examine?

The researchers drew a stratified sample of **400 SEC-registered investment advisers** from a population of **16,223 firms**, crossing adviser type with assets-under-management (AUM) quartiles. The analysis uses **388 available brochures**, classified with a prespecified five-label typology.

## How often do advisers disclose using artificial intelligence?

**23.7%** of the analyzed brochures disclosed some form of AI use (95% confidence interval: **19.7%–28.2%**). The survey-weighted estimate for the specified brochure-filing universe was **22.7%**.

These figures describe what the firms disclose in these documents. They do **not** estimate how many firms actually use AI.

## Do advisers discuss AI risks more often than AI use?

**27.6%** of brochures contained AI-related risk language, versus **23.7%** disclosing any AI use. Mentioning AI as a risk does not necessarily mean the adviser has deployed an AI system.

## Are AI disclosures associated with firm size?

Yes. Observed AI-use disclosure increased from **10.4%** in the smallest AUM quartile to **43.8%** in the largest. This is a cross-sectional relationship, not evidence that firm size causes AI adoption or disclosure.

## Do adviser types differ in their disclosures?

The study compares private-fund advisers with wealth/retail advisers as part of its stratified sampling design and reports differences in disclosure by adviser type and size. See the published article for subgroup estimates and the corresponding statistical analyses.

## Why can reported AI prevalence differ across studies?

The result depends on the **construct being measured**, the population studied, and the weighting approach. The article reports estimates of **9.9%, 13.1%, and 23.7%** under differing measurement choices. They should not be interpreted as three equivalent measures of actual AI adoption.

## Can large language models classify AI disclosures reliably?

The paper evaluates its classification approach rather than assuming it is accurate. The repository reports an independent cross-model-family evaluation for any-use classification (**κ = 0.738**) and targeted human verification on **158 cases**, including precision and sensitivity estimates. The journal article explains the validation design and its limitations.

## Do advisers' websites and regulatory brochures convey the same information?

For **283 firms** with both sources available, the raw AI-use disclosure rates were **23.0% in brochures** and **5.7% on websites**. After accounting for document length, the study could not distinguish the venue effect from zero. The raw difference therefore should not be attributed to the venue alone.

## Does this study show whether investment advisers are AI-washing?

No. A screening method based on language relevant to earlier SEC AI-washing enforcement actions identified **five brochures out of 388** for review. **None was adjudicated as an unsubstantiated promotional claim**. The study does not establish an industry-wide AI-washing rate or wrongdoing by any particular firm.

## Can other researchers reproduce the results?

Yes. The authors provide a frozen, pseudonymized dataset and deterministic computational pipeline through the [source repository](https://github.com/samirrc2/AI-Use-and-Risk-Disclosure) and the [Code Ocean reproducibility capsule](https://doi.org/10.24433/CO.3404788.v2). The computational artifact has its own DOI, distinct from the journal article's DOI.

## What does the study not establish?

It does not estimate actual AI deployment across the advisory industry, assess whether AI improves investment returns or investment advice, establish causal effects of firm characteristics, or identify firms that violated securities laws.

---

For full methodological details, numerical results, references and limitations, consult the **[published peer-reviewed article](https://doi.org/10.3389/frai.2026.1969257)**.
