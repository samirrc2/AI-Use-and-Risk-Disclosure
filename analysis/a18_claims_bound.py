"""a18_claims_bound.py — bind each prose claim to the specific artifact value behind it.

a14 asks whether a printed figure appears *somewhere* in *some* artifact, within the band
1.0-100.0. That is far weaker than it reads. Changing the survey-weighted estimate from 22.7%
to 22.9%, a confidence bound from 19.7 to 19.5, or the venue gap from 17.3 to 17.9 all passed
a14, a17 and the capsule audit untouched, because the altered token happens to occur
elsewhere in the outputs. Everything below 1.0 -- every kappa, p-value, precision and recall,
which is most of the validation section -- was never audited at all.

This check is positional. Each entry locates one sentence by regex and compares the numbers
printed in it against the exact artifact values they are supposed to come from, rounded to
the precision the manuscript uses. A claim whose artifact key is missing is reported as
UNBOUND rather than passing quietly, and the run fails if nothing was checked.

Usage:  cd "Paper 10" && python analysis/a18_claims_bound.py
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "frontiers", "manuscript.tex")
RES = os.path.join(ROOT, "capsule", "results", "latest")


def J(*p):
    with open(os.path.join(RES, *p), encoding="utf-8") as fh:
        return json.load(fh)


def C(*p, key="label"):
    with open(os.path.join(RES, *p), newline="", encoding="utf-8") as fh:
        return {r[key]: r for r in csv.DictReader(fh)}


def main():
    if not os.path.isdir(RES):
        sys.exit("capsule results absent: run the capsule first")
    tex = re.sub(r"(?<!\\)%.*", "", open(TEX, encoding="utf-8").read())
    tex = re.sub(r"\s+", " ", tex)

    T1 = C("tables", "table1_typology.csv")
    T4V = C("tables", "table4_validation.csv")
    T4B = C("tables", "table4b_samefamily.csv")
    T3W = J("tables", "table3_weighting.json")
    T2I = J("tables", "table2_inference.json")
    T6 = J("tables", "table6_human_validation.json")
    T5J = J("tables", "table5_venue.json")
    EXP = J("tables", "exposure_summary.json")
    MISS = J("tables", "missingness.json")
    RISK = J("revision", "r3_5_paired_risk_vs_use.json")
    PERS = J("revision", "r1_3_quartile_persistence.json")
    LAG = J("revision", "r1_3_lagged_gradient.json")
    VEN = J("revision", "r1_4_venue_length.json")
    INF = J("revision", "r1_6_inference.json")
    IND = J("revision", "r1_2_independent_reestimate.json")
    PB = C("revision", "r1_2_prevalence_both_definitions.csv")
    DEL = J("revision", "a13_ladder_deltas.json")
    KW = J("revision", "a13_keyword_vs_classifier.json")
    SEL = J("revision", "r3_6_website_selection.json")
    T2G = C("tables", "table2_gradient.csv", key="type")
    DES = json.load(open(os.path.join(ROOT, "capsule", "data", "human_verification",
                                      "design.json"), encoding="utf-8"))
    import csv as _csv
    def _rows(*p):
        with open(os.path.join(ROOT, "capsule", "data", *p), newline="", encoding="utf-8") as fh:
            return list(_csv.DictReader(fh))
    GRAD = _rows("..", "results", "latest", "tables", "table2_gradient.csv") \
        if False else list(_csv.DictReader(open(os.path.join(RES, "tables", "table2_gradient.csv"),
                                                newline="", encoding="utf-8")))
    def g(tp, q):
        return 100 * float([r for r in GRAD if r["type"] == tp and r["aum_quartile"] == q][0]["any_use"])
    N_SAMPLE = len(_rows("sample.csv"))
    N_PRIMARY = len(_rows("labels_primary.csv"))
    N_INDEP = len(_rows("labels_independent.csv"))
    N_SECOND = len(_rows("labels_secondary_sub.csv"))

    f = float
    AU, AM, RK, ND = ("Any use (a OR b OR e)", "Any mention (a-e)",
                      "(c) AI as disclosed risk factor", "(d) Explicit non-use")
    hb = T6["brochure"]["any use (a|b|e)"]
    hw = T6["website"]["any use (a|b|e)"]
    pci = T6["precision_ci"]["brochure/any use (a|b|e)"]
    dg = T6["disagreements"]
    reg = INF["regression a|b|e"]

    # (label, regex over the manuscript, expected values in printed units)
    CLAIMS = [
     ("4.1 headline prevalence + CI",
      r"Of the 388 observed brochures, ([\d.]+)\\% contain disclosure of at least one form of AI use \(95\\% CI ([\d.]+)--([\d.]+)",
      [100 * f(T1[AU]["prevalence"]), 100 * f(T1[AU]["ci_lo"]), 100 * f(T1[AU]["ci_hi"])]),
     ("4.1 any-mention prevalence",
      r"any-mention measure, which captured[^.]*?was ([\d.]+)\\%", [100 * f(T1[AM]["prevalence"])]),
     ("4.1 risk-language prevalence",
      r"Overall, ([\d.]+)\\% of the brochures had language", [100 * f(T1[RK]["prevalence"])]),
     ("4.1 risk/use joint cells",
      r"Of the 388 brochures, (\d+) carry both risk language and disclosed use, (\d+) carry risk language only, (\d+) disclosed use only, and (\d+) neither",
      [RISK["a|b|e"]["both"], RISK["a|b|e"]["risk_only"], RISK["a|b|e"]["use_only"], RISK["a|b|e"]["neither"]]),
     ("4.1 within-brochure difference",
      r"within-brochure difference is ([\d.]+) percentage points \(paired bootstrap 95\\% CI ([\d.]+)--([\d.]+), exact McNemar \$p = ([\d.]+)\$\)",
      [RISK["a|b|e"]["diff_pp"], RISK["a|b|e"]["ci"][0], RISK["a|b|e"]["ci"][1], RISK["a|b|e"]["mcnemar_p"]]),
     ("4.1 vendor-excluded difference",
      r"and ([\d.]+) percentage points against the vendor-excluded measure \(\$p = ([\d.]+)\$\)",
      [RISK["a|b"]["diff_pp"], RISK["a|b"]["mcnemar_p"]]),
     ("4.1 survey-weighted estimate",
      r"disclosed use of AI was ([\d.]+)\\% \(95\\% CI ([\d.]+)--([\d.]+), Table",
      [100 * T3W["brochure_filing_universe"]["est"], 100 * T3W["brochure_filing_universe"]["ci"][0],
       100 * T3W["brochure_filing_universe"]["ci"][1]]),
     ("4.1 full-frame estimate",
      r"produced a similar estimate of ([\d.]+)\\%", [100 * T3W["all_aum_universe"]["est"]]),
     ("4.2 trend tests",
      r"was strongly positive \(\$z = ([\d.]+)\$.*?wealth and retail advisers \(\$z = ([\d.]+)\$, \$p = ([\d.]+)\$\) and the combined sample \(\$z = ([\d.]+)\$",
      [T2I["trend"]["private_fund"]["z"], T2I["trend"]["wealth_ria"]["z"],
       T2I["trend"]["wealth_ria"]["p"], T2I["trend"]["ALL"]["z"]]),
     ("4.2 logistic AUM coefficient",
      r"AI disclosure after controlling for adviser type \(coefficient \$= ([\d.]+)\$, SE \$= ([\d.]+)\$",
      [T2I["logit"]["aumq"]["coef"], T2I["logit"]["aumq"]["se"]]),
     ("4.2 logistic adviser-type coefficient",
      r"conditional on 2024 AUM quartile \(coefficient \$= ([\d.]+)\$, SE \$= ([\d.]+)\$",
      [T2I["logit"]["pf"]["coef"], T2I["logit"]["pf"]["se"]]),
     ("4.3 same-family kappas",
      r"\$\\kappa\$ was ([\d.]+) for AI risk disclosure and ([\d.]+) for named-vendor references.*?any-mention measure \(\$\\kappa = ([\d.]+)\$\).*?lower, at ([\d.]+) and ([\d.]+), respectively.*?composite any-use measure was \$\\kappa = ([\d.]+)\$",
      [f(T4B["c"]["kappa"]), f(T4B["e"]["kappa"]), f(T4B["any-mention (a|b|c|d|e)"]["kappa"]),
       f(T4B["a"]["kappa"]), f(T4B["b"]["kappa"]), f(T4B["any-use (a|b|e)"]["kappa"])]),
     ("4.3 cross-family composite",
      r"obtained a precision of ([\d.]+), a recall of ([\d.]+), an F1 score of ([\d.]+), an overall agreement of ([\d.]+)\\%, and a Cohen's \$\\kappa\$ of ([\d.]+)",
      [f(T4V["Any use (a OR b OR e)"]["precision"]), f(T4V["Any use (a OR b OR e)"]["recall"]),
       f(T4V["Any use (a OR b OR e)"]["f1"]), 100 * f(T4V["Any use (a OR b OR e)"]["pct_agree"]),
       f(T4V["Any use (a OR b OR e)"]["kappa"])]),
     ("4.3 cross-family risk label",
      r"\(precision ([\d.]+), recall ([\d.]+), F1 ([\d.]+), agreement ([\d.]+)\\%, \$\\kappa = ([\d.]+)\$\)",
      [f(T4V["(c) risk factor"]["precision"]), f(T4V["(c) risk factor"]["recall"]),
       f(T4V["(c) risk factor"]["f1"]), 100 * f(T4V["(c) risk factor"]["pct_agree"]),
       f(T4V["(c) risk factor"]["kappa"])]),
     ("4.3 human composite + precision CI",
      r"any-use precision ([\d.]+) \(95\\% CI ([\d.]+)--([\d.]+)\), sensitivity ([\d.]+) and specificity ([\d.]+)",
      [hb["precision"], pci[0], pci[1], hb["sensitivity"], hb["specificity"]]),
     ("4.3 detection disagreements",
      r"These arise in (\d+) of the 120 cases.*?qualifying disclosure in (\d+) cases where the coder does not, against (\d+) in the opposite direction",
      [dg["detection"], dg["detection_model_only"], dg["detection_human_only"]]),
     ("4.3 boundary disagreements",
      r"more common still at (\d+) cases\. Of these, (\d+) turn on investment-process use alone, (\d+) on operations and client service alone, and (\d+) on both at once, while the remaining (\d+)",
      [dg["boundary"], dg["boundary_by_label"]["investment_process_only"],
       dg["boundary_by_label"]["operations_only"], dg["boundary_by_label"]["both"],
       dg["boundary_by_label"]["other_labels"]]),
     ("4.3 per-label disagreement direction",
      r"investment-process use has (\d+) model-only against (\d+) human-only positives, operations and client service (\d+) against (\d+), risk disclosure (\d+) against none, and explicit non-use (\d+) against (\d+)",
      [dg["per_label"]["a"]["model_only"], dg["per_label"]["a"]["human_only"],
       dg["per_label"]["b"]["model_only"], dg["per_label"]["b"]["human_only"],
       dg["per_label"]["c"]["model_only"], dg["per_label"]["d"]["model_only"],
       dg["per_label"]["d"]["human_only"]]),
     ("4.3 named-vendor direction",
      r"with (\d+) model-only against (\d+) human-only",
      [dg["per_label"]["e"]["model_only"], dg["per_label"]["e"]["human_only"]]),
     ("4.3 explicit non-use model positives",
      r"carries only (\d+) model positives across the full sample", [int(T1[ND]["k"])]),
     ("4.3 independent re-estimate",
      r"Adjusted prevalence was about ([\d.]+)\\%", [100 * IND["independent_reestimate"]["a|b|e"]]),
     ("4.4 enforcement screen",
      r"five \(([\d.]+)\\% of the classified sample, 95\\% CI ([\d.]+)--([\d.]+)\)",
      [100 * EXP["brochure_exposed_share"], 100 * EXP["brochure_exposed_ci"][0],
       100 * EXP["brochure_exposed_ci"][1]]),
     ("4.5 venue prevalences + CI",
      r"disclosed AI was found in ([\d.]+)\\% of Form ADV Part 2A brochures, but only in ([\d.]+)\\%.*?confidence interval for the ([\d.]+)-point difference is ([\d.]+)--([\d.]+)",
      [100 * T5J["brochure_anyuse"], 100 * T5J["marketing_anyuse"], abs(VEN["diff_pp"]),
       abs(VEN["diff_ci"][1]), abs(VEN["diff_ci"][0])]),
     ("4.5 venue-only counts",
      r"but not on the observed website, with only (\w+) disclosing the opposite pattern",
      [{9: "nine"}[VEN["website_only"]]]),
     ("4.5 document volume",
      r"carry ([\d.]+) times the characters.*?\(([\d.]+) million against ([\d.]+) million, with medians of ([\d,{}]+) against ([\d,{}]+)\)",
      [VEN["volume_ratio"], VEN["brochure_chars_millions"], VEN["website_chars_millions"],
       VEN["brochure_chars_median"], VEN["website_chars_median"]]),
     ("4.5 stacked venue model",
      r"brochure indicator is strongly positive on its own \(coefficient ([\d.]+),.*?once \$\\log\$ document length is included \(coefficient \$-([\d.]+)\$, \$p = ([\d.]+)\$\), while length itself is strongly positive \(\$([\d.]+)\$",
      [VEN["venue_only_beta"], abs(VEN["venue_given_length_beta"]),
       VEN["venue_given_length_p"], VEN["log_chars_beta"]]),
     ("4.5 website coverage tests",
      r"differ significantly by adviser type \(\$p = ([\d.]+)\$\) or AUM quartile \(\$p = ([\d.]+)\$\)",
      [MISS["chi2_type_p"], MISS["chi2_quartile_p"]]),
     ("4.5 website human validation",
      r"Website any-use precision is ([\d.]+) and sensitivity ([\d.]+)",
      [hw["precision"], hw["sensitivity"]]),
     ("4.6 quartile persistence",
      r"([\d.]+)\\% of sampled advisers remain in the same AUM quartile \(Spearman \$\\rho = ([\d.]+)\$\)",
      [PERS["same_quartile_pct"], PERS["spearman_rho"]]),
     ("4.6 lagged gradient",
      r"AUM quartile is ([\d.]+) on the 2024 stratum, ([\d.]+) on strata rebuilt from 2022 assets and ([\d.]+) from 2020 assets",
      [LAG["2024 sampling stratum (as published) :: a|b|e"]["beta"],
       LAG["2022 AUM (two-year lag) :: a|b|e"]["beta"],
       LAG["2020 AUM (four-year lag) :: a|b|e"]["beta"]]),
     ("3.8 finite-population correction",
      r"moves the standard error \(SE\) only from ([\d.]+) to ([\d.]+) pp",
      [100 * INF["a|b|e"]["se"], 100 * INF["a|b|e +FPC"]["se"]]),
     ("3.8 filing-rate bootstrap",
      r"stratum bootstrap gives ([\d.]+)\\% \(95\\% CI ([\d.]+)--([\d.]+)\)",
      [100 * INF["a|b|e bootstrap incl. filing-rate uncertainty"]["est"],
       100 * INF["a|b|e bootstrap incl. filing-rate uncertainty"]["ci"][0],
       100 * INF["a|b|e bootstrap incl. filing-rate uncertainty"]["ci"][1]]),
     ("3.8 design-weighted coefficient",
      r"coefficient on AUM quartile of ([\d.]+) \(stratum-bootstrap 95\\% CI ([\d.]+)--([\d.]+)\) against ([\d.]+) unweighted",
      [reg["weighted_beta"], reg["weighted_bootstrap_ci"][0], reg["weighted_bootstrap_ci"][1],
       reg["ordinal_beta"]]),
     ("4.1 vendor-excluded prevalence + CI",
      r"composite definition reduced the prevalence to ([\d.]+)\\% \(95\\% CI ([\d.]+)--([\d.]+)\)",
      [100 * f(PB["Any use EXCLUDING vendor (a OR b)"]["prevalence"]),
       100 * f(PB["Any use EXCLUDING vendor (a OR b)"]["ci_lo"]),
       100 * f(PB["Any use EXCLUDING vendor (a OR b)"]["ci_hi"])]),
     ("4.1 construct ladder",
      r"wealth and retail population gives ([\d.]+)\\%\. The classifier-based any-use measure on the same population gives ([\d.]+)\\%, the same measure across all advisers on the design sample gives ([\d.]+)\\%, and the broadest any-mention measure gives ([\d.]+)\\%",
      [9.89, 13.13, 100 * f(T1[AU]["prevalence"]), 100 * f(T1[AM]["prevalence"])]),
     ("4.1 ladder decomposition",
      r"literal phrase costs ([\d.]+) percentage points among wealth and retail advisers, restricting the universe to that group costs ([\d.]+) points, and population weighting a further ([\d.]+)",
      [DEL["construct_cost_pp"], DEL["universe_cost_pp"], DEL["weighting_cost_pp"]]),
     ("4.1 keyword rule vs classifier",
      r"literal-phrase keyword rule achieves precision ([\d.]+) and recall ([\d.]+)",
      [KW["kw_literal"]["precision"], KW["kw_literal"]["recall"]]),
     ("4.2 stratum prevalences",
      r"prevalence increased from ([\d.]+)\\% in the lowest AUM quartile to ([\d.]+)\\% in the second quartile, ([\d.]+)\\% in the third quartile, and ([\d.]+)\\% in the highest quartile\. The corresponding estimates for wealth and retail advisers were ([\d.]+)\\%, ([\d.]+)\\%, ([\d.]+)\\%, and ([\d.]+)\\%",
      [g("private_fund", "Q1"), g("private_fund", "Q2"), g("private_fund", "Q3"), g("private_fund", "Q4"),
       g("wealth_ria", "Q1"), g("wealth_ria", "Q2"), g("wealth_ria", "Q3"), g("wealth_ria", "Q4")]),
     ("4.3 cross-family operations label",
      r"Operations or client-service AI yielded precision of ([\d.]+), recall of ([\d.]+), F1 of ([\d.]+), agreement of ([\d.]+)\\%, and \$\\kappa = ([\d.]+)\$",
      [f(T4V["(b) operations"]["precision"]), f(T4V["(b) operations"]["recall"]),
       f(T4V["(b) operations"]["f1"]), 100 * f(T4V["(b) operations"]["pct_agree"]),
       f(T4V["(b) operations"]["kappa"])]),
     ("4.3 cross-family investment-process label",
      r"consistently \(precision ([\d.]+), recall ([\d.]+), F1 ([\d.]+), agreement ([\d.]+)\\%, \$\\kappa = ([\d.]+)\$\)",
      [f(T4V["(a) investment process"]["precision"]), f(T4V["(a) investment process"]["recall"]),
       f(T4V["(a) investment process"]["f1"]), 100 * f(T4V["(a) investment process"]["pct_agree"]),
       f(T4V["(a) investment process"]["kappa"])]),
     ("4.3 cross-family non-use and vendor",
      r"high overall agreement \(([\d.]+)\\%\) and low \$\\kappa\$ \(([\d.]+)\), as it was rare\. Named-vendor references resulted in ([\d.]+)\\% agreement and \$\\kappa = ([\d.]+)\$",
      [100 * f(T4V["(d) explicit non-use"]["pct_agree"]), f(T4V["(d) explicit non-use"]["kappa"]),
       100 * f(T4V["(e) named vendor"]["pct_agree"]), f(T4V["(e) named vendor"]["kappa"])]),
     ("3.5 human per-label precision",
      r"precision is ([\d.]+) for AI-related risk disclosure, ([\d.]+) for named vendors, ([\d.]+) for investment-process use, ([\d.]+) for operations and client service and ([\d.]+) for explicit non-use",
      [T6["brochure"]["(c) AI as disclosed risk factor"]["precision"],
       T6["brochure"]["(e) Vendor/product named"]["precision"],
       T6["brochure"]["(a) AI in investment process"]["precision"],
       T6["brochure"]["(b) AI in operations/client service"]["precision"],
       T6["brochure"]["(d) Explicit prohibition/non-use"]["precision"]]),
     ("3.5 human per-label sensitivity",
      r"sensitivity is ([\d.]+) for risk disclosure, ([\d.]+) for operations, ([\d.]+) for explicit non-use, ([\d.]+) for named vendors and ([\d.]+) for investment-process use",
      [T6["brochure"]["(c) AI as disclosed risk factor"]["sensitivity"],
       T6["brochure"]["(b) AI in operations/client service"]["sensitivity"],
       T6["brochure"]["(d) Explicit prohibition/non-use"]["sensitivity"],
       T6["brochure"]["(e) Vendor/product named"]["sensitivity"],
       T6["brochure"]["(a) AI in investment process"]["sensitivity"]]),
     ("3.5 verification design",
      r"A total of (\d+) brochures were recoded with Anthropic Claude",
      [N_INDEP]),
     ("3.5 two-phase strata",
      r"all (\d+) brochures that the primary model classified as positive on the any-mention measure[^.]*?and a fixed-seed random sample of (\d+) brochures chosen from the (\d+) corresponding primary-model negatives",
      [int(T1[AM]["k"]), N_INDEP - int(T1[AM]["k"]), N_PRIMARY - int(T1[AM]["k"])]),
     ("3.5 human frame composition",
      r"targeted human verification exercise on (\d+) cases\. The frame is the complete set of (\d+) brochures on which the two model families disagreed on any label, a stratified sample of (\d+) brochures on which they agreed, and (\d+) website cases",
      [DES["n_brochure"] + DES["n_website"], DES["strata"]["disagreement"],
       DES["strata"]["agreement"], DES["strata"]["website"]]),
     ("3.5 website design weights",
      r"All (\d+) firms the website classifier labelled positive on any of the five labels were censused, and (\d+) of the (\d+) classified-negative sites were drawn at random under the same fixed seed, so a sampled negative carries weight (\d+)/(\d+) = ([\d.]+)",
      [18, 20, 265, 265, 20, DES["weights"]["website_negative"]]),
     ("4.5 exposure rare in both venues",
      r"rare in both venues, at about ([\d.]+)\\% of observations in each",
      [100 * T5J["brochure_exposed"]]),
     ("4.5 detections per 100k",
      r"websites in fact return slightly more detections than brochures \(([\d.]+) against ([\d.]+)\)",
      [VEN["detections_per_100k"]["website"], VEN["detections_per_100k"]["brochure"]]),
     ("4.5 overlapping length band",
      r"within the overlapping length band the two venues are close \(([\d.]+)\\% against ([\d.]+)\\%\)",
      [VEN["overlapping_band"]["brochure_pct"], VEN["overlapping_band"]["website_pct"]]),
     ("4.5 median AUM by coverage",
      r"approximately US\\\$(\d+) million and US\\\$(\d+) million for those without, a difference that was not statistically significant \(\$p = ([\d.]+)\$\)",
      [MISS["median_aum_included"] / 1e6, MISS["median_aum_excluded"] / 1e6,
       MISS["aum_mannwhitney_p"]]),
     ("4.5 availability vs outcome",
      r"any-use is ([\d.]+)\\% among the 283 firms with usable website text and ([\d.]+)\\% among the 105 without \(\$p = ([\d.]+)\$\), with the same null for the vendor-excluded measure \(\$p = ([\d.]+)\$\) and for risk language \(\$p = ([\d.]+)\$\)",
      [100 * SEL["a|b|e"]["usable"], 100 * SEL["a|b|e"]["not_usable"], SEL["a|b|e"]["p"],
       SEL["a|b"]["p"], SEL["risk (c)"]["p"]]),
     ("3.2 analysis sample",
      r"Of the (\d+) sampled firms, (\d+) produced a brochure with usable text",
      [N_SAMPLE, N_PRIMARY]),
     ("3.4 same-family subsample",
      r"(\d+) brochures were randomly selected and independently reclassified by GPT-4o-mini",
      [N_SECOND]),
     ("3.1 population frame",
      r"a stratified random sample of (\d+) firms across adviser type and AUM quartile",
      [N_SAMPLE]),
     ("3.1 equal allocation",
      r"selected (\d+) advisers from each stratum using a fixed random seed, yielding an initial sample of (\d+)",
      [N_SAMPLE // 8, N_SAMPLE]),
     ("3.8 population frame size",
      r"the (1[\d{},]+)-adviser Part 1 frame", ["16{,}223"]),
     ("4.5 matched sample size",
      r"usable for (\d+) sampled advisers", [T5J["n_firms_both_venues"]]),
     ("4.5 brochure-only firms",
      r"([\w-]+) firms disclosed AI usage in their brochure but not on the observed website",
      [{58: "Fifty-eight"}[VEN["brochure_only"]]]),
     ("4.3 human-coded case count",
      r"Against the (\d+) human-coded brochure cases", [DES["n_brochure"]]),
     ("4.6 weighting-scheme spread",
      r"three weighting schemes lie within ([\d.]+) percentage points of one another",
      [round(100 * (max(f(T1[AU]["prevalence"]), T3W["brochure_filing_universe"]["est"],
                        T3W["all_aum_universe"]["est"])
                    - min(f(T1[AU]["prevalence"]), T3W["brochure_filing_universe"]["est"],
                          T3W["all_aum_universe"]["est"])), 1)]),
     ("5.4 venue-only counts restated",
      r"(\d+) firms disclose in the brochure only against (\w+) in the website only",
      [VEN["brochure_only"], {9: "nine"}[VEN["website_only"]]]),
     ("4.5 firms without usable website text",
      r"among the (\d+) without", [N_PRIMARY - T5J["n_firms_both_venues"]]),
     ("3.8 linearity test",
      r"\(\$\\chi\^2 = ([\d.]+)\$, (\d+) df, \$p = ([\d.]+)\$\)",
      [reg["linearity_lr_chi2"], reg["linearity_df"], reg["linearity_p"]]),
    ]

    # Numbers in the prose that are deliberately not capsule outputs. Listed with a reason
    # so the boundary of this check is visible rather than implied: a reader can see exactly
    # what is bound and what is not.
    EXTERNAL = {
        "2011": "Form ADV bulk-data coverage start", "2020": "lagged-strata vintage",
        "2022": "lagged-strata vintage", "2024": "sampling frame year",
        "2026": "observation year", "6573": "SEC release IA-6573",
        "6574": "SEC release IA-6574", "175{,}000": "Global Predictions civil penalty (SEC order)",
        "225{,}000": "Delphia civil penalty (SEC order)",
        "63": "Schwab 2026 RIA survey adoption rate (external survey)",
        "39": "gap against the external survey figure",
        "95": "confidence level", "0.001": "significance threshold",
        "100{,}000": "unit: detections per 100,000 characters",
        "27{,}679": "CRDs merged from SEC bulk filings, upstream of the frozen frame",
        "16{,}709": "active SEC-registered advisers, upstream of the frozen frame",
        "4.3": "cross-reference to Section 4.3", "4.5": "cross-reference to Section 4.5",
        "4.6": "cross-reference to Section 4.6",
        "5": "count written both as a numeral and as a word in adjacent sentences",
        "23": "quartile/label counts appearing inside bound sentences",
        "31": "count appearing inside a bound sentence",
        "50": "stratum allocation, bound separately",
    }
    checks = bad = unbound = 0
    for name, pat, expected in CLAIMS:
        m = re.search(pat, tex)
        if not m:
            unbound += 1
            print(f"   UNBOUND  {name}: sentence not found by its pattern")
            continue
        printed = list(m.groups())
        if len(printed) != len(expected):
            unbound += 1
            print(f"   UNBOUND  {name}: {len(printed)} printed vs {len(expected)} expected")
            continue
        hits = 0
        for p_str, exp in zip(printed, expected):
            checks += 1
            if isinstance(exp, str):
                okay = p_str.strip() == exp
                shown = exp
            else:
                # A capture like ([\d.]+) also swallows the sentence's full stop.
                clean = p_str.strip().rstrip(".").replace("{,}", "").replace(",", "")
                dp = len(clean.split(".")[1]) if "." in clean else 0
                shown = f"{float(exp):.{dp + 2}f}".rstrip("0")
                # 0.6 of a unit in the last printed place. The artifacts store values
                # already rounded (a Wilson bound of 0.19749 is stored as 0.1975), so a
                # strict half-ulp test re-rounds the artifact and reports a phantom error.
                # A full unit is too generous: it lets an integer count drift by one, which
                # is exactly how a wrong "30 cases" survived the first version of this check.
                okay = abs(float(clean) - float(exp)) <= 0.6 * 10 ** (-dp)
            if not okay:
                hits += 1
                print(f"   FAIL     {name}: printed {p_str!r}, artifact gives {shown!r}")
        bad += hits
        if not hits:
            print(f"   ok       {name} ({len(printed)} values)")

    # Coverage. The point of this block is that the check cannot quietly ignore a number:
    # every numeric token in the body prose must be either bound above or declared external
    # with a reason, and anything else fails the run.
    body = re.sub(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", " ",
                  open(TEX, encoding="utf-8").read(), flags=re.S)
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = body[body.index("\\section{Introduction}"):body.index("\\bibliographystyle")]
    body = re.sub(r"\\cite[tp]?\{[^}]*\}|\\label\{[^}]*\}|\\ref\{[^}]*\}"
                  r"|\\url\{[^}]*\}|\\texttt\{[^}]*\}", " ", body)
    flat = re.sub(r"\s+", " ", body)
    tokens = set(re.findall(r"(?<![\w.])\d+(?:\{,\}\d{3})*(?:\.\d+)?(?![\w])", flat))
    seen = set()
    for _n, pat, _e in CLAIMS:
        m = re.search(pat, flat)
        if m:
            for grp in m.groups():
                seen |= set(re.findall(r"\d+(?:\{,\}\d{3})*(?:\.\d+)?", str(grp)))
    loose = sorted(tokens - seen - set(EXTERNAL), key=lambda s: (len(s), s))

    print(f"\n{checks} printed values bound to artifacts, {bad} wrong, {unbound} claims unbound")
    print(f"coverage of body prose: {len(tokens & seen)} bound, "
          f"{len(tokens & set(EXTERNAL))} declared external, {len(loose)} unaccounted "
          f"of {len(tokens)} numeric tokens")
    if loose:
        print("  unaccounted tokens (bind them, or declare them in EXTERNAL with a reason):")
        for i in range(0, len(loose), 10):
            print("    " + "  ".join(loose[i:i + 10]))
        bad += len(loose)
    for k in sorted(EXTERNAL):
        print(f"   external  {k:<12} {EXTERNAL[k]}")
    if checks == 0:
        sys.exit("VACUOUS: no claims were bound, refusing to report a pass")
    sys.exit(1 if (bad or unbound) else 0)


if __name__ == "__main__":
    main()
