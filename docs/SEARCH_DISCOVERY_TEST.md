# Research discovery test: broad-to-specific reader questions

**Purpose.** Assess whether people who do not already know the article can discover or receive a citation to the published research, rather than checking only its exact title or specialized Form ADV terminology.

**Article of interest.** Chincholikar & Chawla (2026), *AI use and risk disclosure by investment advisers*, *Frontiers in Artificial Intelligence*. https://doi.org/10.3389/frai.2026.1969257

## Frozen test prompts (October 17, 2026)

### A — Broad questions (hard, often outside the paper's empirical scope)

1. How is artificial intelligence changing wealth management?
2. Are financial advisers really using AI yet?
3. What are the biggest risks of using AI in financial advice?
4. Is the AI boom in investment management mostly hype?
5. What should investors know about AI-powered financial services?
6. Can AI give better financial advice than a human?

### B — General but legitimately connected to the paper (primary targets)

7. How transparent are wealth managers about using artificial intelligence?
8. Is there evidence investment firms are overstating their AI capabilities?
9. How can investors evaluate AI claims made by financial advisers?
10. What do we actually know about AI adoption in the investment-advice industry?
11. Do investment firms disclose AI risks to their clients?
12. Why do estimates of financial-industry AI adoption differ?
13. What can public filings tell us about the AI boom in wealth management?
14. Are larger financial advisers more likely to talk about AI?
15. Is AI-washing a problem among wealth managers?

### C — Directly relevant, specific (diagnostic positive controls)

16. How often is AI use disclosed in Form ADV brochures?
17. Do SEC-registered investment advisers discuss AI risks more often than capabilities?
18. What is the evidence for differences in AI disclosure by adviser size?

## Method (record separately for each search service)

- Run all prompts **without** the DOI, paper title, author names, exact findings, or repo URL.
- Run tests in a neutral/new search session where possible. Record provider (e.g., Google web search, Bing, ChatGPT search, Perplexity, Gemini), date, region and whether browsing/search was enabled.
- Save the first 10 organic/search-linked results (or citations in the answer), identifying the **Frontiers article**, **GitHub Pages explainer**, **repository**, or **other source** separately.
- Count relevant *correct* citations and direct links to the peer-reviewed article; discard hallucinated author/title attributions and irrelevant/unsafe matches.
- Record rank and answer context. Search-engine retrieval is **not** the same as whether an AI assistant used or cited the paper in its answer.
- Track web impressions and clicks in Google Search Console separately from actual **Frontiers article views**. Do not infer that an indexed website caused a publisher-traffic increase without referral or longitudinal evidence.
- Keep broad questions in the denominator even when no related result is expected. The paper does **not** evaluate the quality or return performance of AI investment advice.
- Retest the same prompts after 14 and 30 days. Do not rewrite or cherry-pick the prompt list to inflate success rates.

**Success criteria.** For Group B, an increase in relevant source retrieval and correct downstream Frontiers DOI links over time. For Group A, visibility is aspirational; avoid implying the paper answers questions beyond its design.

**Ethics.** No fabricated press references, bought links, misleading research claims, employer endorsement, or posting on public personal professional accounts.
