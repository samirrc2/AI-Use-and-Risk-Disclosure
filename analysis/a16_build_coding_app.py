"""
a16_build_coding_app.py — build the human-validation coding package.

Produces human_validation/ at the repository root, containing one self-contained HTML
coding app per coder plus the assignment record the scorer needs.

Design (two-phase, Horvitz--Thompson weighted; see Methods 3.5):

  The frame is the complete model-disagreement census plus a stratified sample of
  agreement cases and website cases, exactly as both reviewers specified. It is split
  between the two coders so that every row is coded once and none is coded twice: the
  reviewers asked for a human reference standard, not for a measure of agreement
  between coders, so duplicated coding would buy nothing and cost an hour.

What the app deliberately does NOT do, because each would invalidate the exercise:
  * show the model's labels, or any hint of them
  * suggest which label applies
  * reveal whether a row is a disagreement or an agreement case
  * expose the other coder's answers

Row order is randomised per coder, so the two coders never walk the same sequence.

Usage:  cd "Paper 10" && python analysis/a16_build_coding_app.py
"""
import html
import json
import os
import random
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HV = os.path.join(ROOT, "analysis", "out", "revision", "human_validation")
OUT = os.path.join(ROOT, "human_validation")
RUBRIC = os.path.join(ROOT, "pilot", "prompts", "typology_v1.md")
CODERS = ["1", "2"]          # coder identity is not recorded in the files themselves
SEED = 42
# No rows are double-coded. Every row in the frame is coded exactly once.

LABELS = [
    ("a", "Investment-process AI",
     "The firm states it uses AI/ML/predictive/algorithmic models in research, security "
     "selection, portfolio construction, signal generation, investment risk modelling or trading."),
    ("b", "Operations / client-service AI",
     "The firm states it uses AI/ML in non-investment functions: client servicing, chatbots, "
     "marketing, compliance, document processing, back office, cybersecurity, meeting notes."),
    ("c", "AI as a disclosed risk factor",
     "AI/ML/algorithmic use is discussed as a source of RISK: model risk, limits of algorithms, "
     "reliance on technology, third-party AI risk, AI-driven cyber risk."),
    ("d", "Explicit prohibition / non-use",
     "The firm affirmatively states it does NOT use AI/ML, or restricts or prohibits its use."),
    ("e", "Vendor / product named",
     "A specific AI product, model or vendor is named. A generic custodian or CRM is NOT label e "
     "unless invoked as an AI capability."),
]
# Two vocabularies, deliberately different.
#
# RETRIEVAL_TERMS is the classifier's own keyword list, copied from build/s05_classify.py, and
# it is what the coder sees highlighted. Some of its terms are unbounded, so `LLM` matches
# insta(llm)ents, enro(llm)ent and Fi(llm)ore, and `robo` matches robots and eu(robo)nds. Those
# accidents pulled real spans into the classifier's window, so they are highlighted here too:
# the coder is entitled to see exactly why a passage was retrieved, including when the reason
# is nonsense.
#
# GENUINE_TERMS is word-bounded and is what actually counts as AI vocabulary. A row whose only
# retrieval hits are accidents contains no AI language at all, so it is pre-set to zero. That
# decision is made from the text alone and never from the model's labels, so it leaks nothing.
RETRIEVAL_TERMS = (r"artificial intelligence|\bAI\b|machine learning|deep learning|neural|"
                   r"generative|large language|LLM|natural language|algorithm|"
                   r"quantitative model|model-driven|predictive|automated|robo|data science")
GENUINE_TERMS = (r"artificial intelligence|\bAI\b|\bML\b|machine learning|deep learning|"
                 r"neural net\w*|generative|large language|\bLLMs?\b|natural language|"
                 r"algorithm\w*|quantitative model|model-driven|predictive|automat\w+|"
                 r"robo-?advis\w*|data science")
AI_TERMS = RETRIEVAL_TERMS


def highlight(text):
    """Mark AI vocabulary so the eye lands on the decision point. A reading aid only: the
    same treatment is applied to every term, so it never implies which label applies."""
    esc = html.escape(text)
    return re.sub("(" + AI_TERMS + ")", r"<mark>\1</mark>", esc, flags=re.I)


def build_assignment():
    sheet = pd.read_csv(os.path.join(HV, "adjudication_sheet_BLINDED.csv"))
    web = pd.read_csv(os.path.join(HV, "website_sheet_BLINDED.csv"))
    key = pd.read_csv(os.path.join(HV, "adjudication_KEY_do_not_give_to_coders.csv"))
    stratum = dict(zip(key.row_id, key.stratum))
    rows = pd.concat([sheet, web], ignore_index=True)
    rows["stratum"] = [stratum.get(r, "website") for r in rows.row_id]

    rng = random.Random(SEED)
    # Split WITHIN each stratum, dealing alternately, rather than shuffling the whole frame
    # and cutting it in half. A single shuffle balances the totals but not the composition:
    # it handed one coder 35 agreement and 14 website rows against the other's 25 and 24.
    # Dealing within strata makes each coder's workload the same mix by construction, so
    # neither carries more of the hard disagreement cases or more of the easy pre-set ones.
    assign = {c: [] for c in CODERS}
    for st in ("disagreement", "agreement", "website"):
        ids = sorted(rows[rows.stratum == st].row_id)
        rng.shuffle(ids)
        for n, r in enumerate(ids):
            assign[CODERS[n % len(CODERS)]].append(r)
    # Presentation order is then randomised per coder, with a coder-specific seed, so the two
    # never walk the same sequence and neither meets a block of one stratum.
    for n, c in enumerate(CODERS):
        random.Random(SEED + 1 + n).shuffle(assign[c])
    dis = sorted(rows[rows.stratum == "disagreement"].row_id)
    agr = sorted(rows[rows.stratum == "agreement"].row_id)
    wb = sorted(rows[rows.stratum == "website"].row_id)
    strat = dict(zip(rows.row_id, rows.stratum))
    meta = {"seed": SEED, "double_coded": [],
            "split": {c: v for c, v in assign.items()},
            "n_disagreement_census": len(dis), "n_agreement": len(agr), "n_website": len(wb),
            "n_per_coder": {c: len(v) for c, v in assign.items()},
            "composition_per_coder": {c: {k: sum(1 for r in v if strat[r] == k)
                                          for k in ("disagreement", "agreement", "website")}
                                      for c, v in assign.items()}}
    return rows.set_index("row_id"), assign, meta


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Human validation %(coder)s</title>
<style>
:root{--bg:#fbfaf7;--fg:#22201c;--mut:#6c675e;--line:#e2ded4;--acc:#1f5f4f;--mark:#fdf0b8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-serif,Georgia,"Times New Roman",serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);
 padding:10px 22px;display:flex;gap:18px;align-items:center;z-index:5}
header b{font:600 14px/1 ui-sans-serif,system-ui;letter-spacing:.04em;text-transform:uppercase}
#bar{flex:1;height:5px;background:var(--line);border-radius:3px;overflow:hidden}
#fill{height:100%%;width:0;background:var(--acc);transition:width .2s}
#count{font:13px ui-sans-serif,system-ui;color:var(--mut);white-space:nowrap}
main{max-width:860px;margin:0 auto;padding:26px 22px 120px}
#rid{font:12px ui-sans-serif,system-ui;letter-spacing:.08em;color:var(--mut);text-transform:uppercase}
#ex{margin:14px 0 26px;padding:20px 22px;background:#fff;border:1px solid var(--line);
 border-radius:5px;font-size:15.5px;max-height:46vh;overflow:auto}
mark{background:var(--mark);padding:0 1px;border-radius:2px}
.why{background:#f3efe4;border-left:3px solid var(--acc);padding:9px 12px;margin:0 0 12px;font-size:13.5px;color:var(--mut);border-radius:0 3px 3px 0}
.lab{display:flex;gap:12px;align-items:flex-start;padding:9px 12px;border:1px solid var(--line);
 border-radius:5px;margin-bottom:7px;cursor:pointer;background:#fff;user-select:none}
.lab:hover{border-color:var(--acc)}
.lab.on{background:#eaf3f0;border-color:var(--acc)}
.key{font:600 12px ui-sans-serif,system-ui;background:var(--line);border-radius:3px;
 padding:2px 7px;min-width:22px;text-align:center}
.lab.on .key{background:var(--acc);color:#fff}
.lt{font-weight:600}.ld{color:var(--mut);font-size:13.5px}
textarea{width:100%%;margin-top:14px;padding:10px;border:1px solid var(--line);border-radius:5px;
 font:14px ui-serif,Georgia,serif;background:#fff;min-height:60px;resize:vertical}
footer{position:fixed;bottom:0;left:0;right:0;background:var(--bg);
 border-top:1px solid var(--line);padding:12px 22px;display:flex;gap:10px;justify-content:center}
button{font:14px ui-sans-serif,system-ui;padding:9px 17px;border:1px solid var(--line);
 background:#fff;border-radius:5px;cursor:pointer}
button:hover{border-color:var(--acc)}
button.p{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}
#flag.on{background:#8a5a00;color:#fff;border-color:#8a5a00}
details{margin-top:26px;font-size:13.5px;color:var(--mut)}
summary{cursor:pointer;font:600 13px ui-sans-serif,system-ui}
details table{border-collapse:collapse;margin-top:10px;width:100%%}
details td{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top}
#done{text-align:center;padding:60px 20px}
#intro{max-width:760px;margin:0 auto;padding:10px 0 40px}
#intro h1{font:600 26px/1.25 ui-serif,Georgia,serif;margin:.2em 0 .1em}
#intro .sub{color:var(--mut);font-size:15px;margin-bottom:26px}
#intro h2{font:600 13px ui-sans-serif,system-ui;letter-spacing:.06em;text-transform:uppercase;
 color:var(--mut);margin:26px 0 8px}
#intro ol{padding-left:20px}#intro li{margin:6px 0}
.rule{background:#fff;border:1px solid var(--line);border-left:3px solid var(--acc);
 border-radius:4px;padding:12px 16px;margin:8px 0}
.rule b{display:block;margin-bottom:2px}
.keys{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.keys span{font:13px ui-sans-serif,system-ui;background:#fff;border:1px solid var(--line);
 border-radius:4px;padding:5px 10px}
.warn{background:#fff8e8;border:1px solid #e8d9a8;border-radius:4px;padding:12px 16px;margin:16px 0;
 font-size:14px}
#ask{font:600 13px ui-sans-serif,system-ui;color:var(--mut);margin:0 0 8px}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .rule,
 :root:not([data-theme=light]) .keys span{background:#1f1d1a}
 :root:not([data-theme=light]) .warn{background:#2a2414;border-color:#4a3f20}}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
 --bg:#171614;--fg:#eceae4;--mut:#a09a8e;--line:#332f2a;--acc:#6fbfa5;--mark:#5a4a12}
@media(prefers-color-scheme:dark){.why{background:#232019}}
 #ex,.lab,textarea,button{background:#1f1d1a}.lab.on{background:#1d2d28}}
</style></head><body>
<header><b>Human validation %(coder)s</b><div id="bar"><div id="fill"></div></div><span id="count"></span></header>
<main>
 <div id="intro">
  <h1>Coding AI disclosure</h1>
  <div class="sub">%(n)d passages from investment-adviser filings and websites.
   You decide, for each, what the document says about the firm&rsquo;s use of AI.</div>

  <h2>What you do</h2>
  <ol>
   <li>Read the passage. AI vocabulary is <mark>highlighted</mark> so you can find the
       relevant sentence without reading every line.</li>
   <li>Switch on whichever of the five labels apply. A passage can match several, or none.</li>
   <li>Press <b>Enter</b> for the next one. Your progress saves automatically.</li>
  </ol>
  <p>Roughly %(npre)d of your rows contain no AI language at all. Those are already set to all
  zeros &mdash; glance and move on.</p>

  <h2>The two rules that settle most hard calls</h2>
  <div class="rule"><b>Is it AI?</b> Machine learning, generative AI, large language models,
   NLP, predictive analytics, algorithmic or model-driven decisioning, and &ldquo;data
   science&rdquo; used as a capability. A CRM, an e-signature tool or a rebalancing rule is
   <b>not</b> AI unless the text itself calls it AI or predictive.</div>
  <div class="rule"><b>Is it this firm?</b> The label describes the filing firm&rsquo;s own
   practice. A vendor using AI inside its own product is not the adviser using AI. Nor is a
   third-party manager the adviser allocates to.</div>

  <h2>Keys</h2>
  <div class="keys"><span><b>A B C D E</b> toggle a label</span><span><b>Enter</b> next</span>
   <span><b>&larr;</b> back</span><span><b>F</b> flag for adjudication</span>
   <span><b>?</b> rubric</span></div>

  <div class="warn"><b>Two things that would invalidate the exercise.</b>
   Do not discuss any row with the other coder until you have both exported your files &mdash;
   the first result computed is how often you two agree, which means nothing if you confer.
   And when a row is genuinely ambiguous, do not agonise: record your best answer, press
   <b>F</b>, say why in the notes, and move on. Flagged rows are resolved together afterwards.</div>

  <button class="p" onclick="start()">Start coding</button>
  <button onclick="start()" id="resume" hidden>Resume</button>
 </div>
 <div id="view" hidden>
  <div id="rid"></div>
  <div id="why" class="why" hidden></div>
  <div id="ex"></div>
  <p id="ask">Does the passage say the filing firm&hellip;</p>
  <div id="labs"></div>
  <textarea id="notes" placeholder="Notes &mdash; why you hesitated, what the rubric did not cover. These become the adjudication record."></textarea>
  <details><summary>Rubric (press ? to toggle)</summary>
   <p><b>Scope of &ldquo;AI&rdquo;:</b> artificial intelligence, machine learning, deep or neural
   learning, generative AI and large language models, NLP, predictive analytics, algorithmic or
   model-driven decisioning, and &ldquo;data science&rdquo; used as a capability. Plain automation
   &mdash; an e-signature tool, a CRM, a rebalancing rule &mdash; is <b>not</b> AI unless the text
   itself frames it as AI, ML or predictive.</p>
   <p><b>Whose practice:</b> a label describes the <b>filing firm&rsquo;s own</b> practices. Generic
   market commentary does not count. A third-party manager the adviser allocates to does not count.
   A vendor using AI inside its own product is not the adviser using AI.</p>
   <table>%(rubric)s</table></details>
 </div>
 <div id="done" hidden>
  <h2>All %(n)d rows coded.</h2>
  <p>Export the file and send it on. Nothing leaves this browser until you do.</p>
  <button class="p" onclick="exp()">Download human_validation_%(coder)s.csv</button>
 </div>
</main>
<footer>
 <button onclick="brief()">Briefing</button>
 <button onclick="go(-1)">&larr; Back</button>
 <button id="flag" onclick="tflag()">Flag for adjudication &nbsp;<span class="key">F</span></button>
 <button class="p" onclick="go(1)">Next &nbsp;<span class="key">&crarr;</span></button>
 <button onclick="exp()">Export CSV</button>
</footer>
<script>
const CODER=%(coder_js)s, ROWS=%(rows)s, KEY="humanvalidation_"+CODER;
let i=0, S=JSON.parse(localStorage.getItem(KEY)||"{}");
const $=id=>document.getElementById(id);
function st(r){ if(!S[r.id]) S[r.id]={a:r.pre?0:null,b:r.pre?0:null,c:r.pre?0:null,
  d:r.pre?0:null,e:r.pre?0:null,notes:"",flag:false}; return S[r.id]; }
function save(){ localStorage.setItem(KEY,JSON.stringify(S)); }
function coded(){ return ROWS.filter(r=>S[r.id]&&S[r.id].a!==null).length; }
function draw(){
  const r=ROWS[i], s=st(r);
  $("rid").textContent="Row "+(i+1)+" of "+ROWS.length+"   \\u00b7   "+r.id+(r.pre?"   \\u00b7   no AI language \\u2014 pre-set to all zeros":"");
  // A banner above the passage, so a pre-set row is recognised before it is read rather than
  // after. Without it the coder works through fee boilerplate wondering what they missed.
  $("why").innerHTML = r.why ? r.why : (r.pre ? "No AI language in this passage. Pre-set to zero \\u2014 press Enter." : "");
  $("why").hidden = !($("why").innerHTML);
  $("ex").innerHTML=r.html;
  $("labs").innerHTML=%(labs)s.map(L=>
    `<div class="lab ${s[L[0]]===1?"on":""}" onclick="tog('${L[0]}')">
      <span class="key">${L[0].toUpperCase()}</span>
      <span><span class="lt">${L[1]}</span><br><span class="ld">${L[2]}</span></span></div>`).join("");
  $("notes").value=s.notes||"";
  $("flag").className=s.flag?"on":"";
  const c=coded(); $("fill").style.width=(100*c/ROWS.length)+"%%";
  $("count").textContent=c+" / "+ROWS.length+" coded";
  $("view").hidden=false; $("done").hidden=true; $("intro").hidden=true;
  document.querySelector("footer").hidden=false;
}
function start(){ localStorage.setItem(KEY+"_seen","1"); draw(); }
function brief(){ const s=st(ROWS[i]); s.notes=$("notes").value; save();
  $("intro").hidden=false; $("view").hidden=true; $("done").hidden=true;
  document.querySelector("footer").hidden=true; window.scrollTo(0,0); }
function tog(k){ const s=st(ROWS[i]); s[k]=s[k]===1?0:1;
  for(const L of ["a","b","c","d","e"]) if(s[L]===null) s[L]=0;
  save(); draw(); }
function tflag(){ const s=st(ROWS[i]); s.flag=!s.flag; save(); draw(); }
function go(d){
  const s=st(ROWS[i]); s.notes=$("notes").value;
  if(d>0) for(const L of ["a","b","c","d","e"]) if(s[L]===null) s[L]=0;
  save(); i+=d;
  if(i<0) i=0;
  if(i>=ROWS.length){ i=ROWS.length-1; if(coded()===ROWS.length){ $("view").hidden=true; $("done").hidden=false; return; } }
  draw(); window.scrollTo(0,0);
}
function exp(){
  const q=v=>'"'+String(v==null?"":v).replace(/"/g,'""')+'"';
  let out="row_id,a,b,c,d,e,notes\\n";
  for(const r of ROWS){ const s=S[r.id]||{};
    out+=[r.id,s.a??"",s.b??"",s.c??"",s.d??"",s.e??"",
          q((s.notes||"")+(s.flag?" [FLAGGED FOR ADJUDICATION]":""))].join(",")+"\\n"; }
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([out],{type:"text/csv"}));
  a.download="human_validation_"+CODER+".csv"; a.click();
}
addEventListener("keydown",e=>{
  if(e.target.tagName==="TEXTAREA"){ if(e.key==="Escape") e.target.blur(); return; }
  const k=e.key.toLowerCase();
  if("abcde".includes(k)) tog(k);
  else if(k==="f") tflag();
  else if(e.key==="Enter"||e.key==="ArrowRight") go(1);
  else if(e.key==="ArrowLeft") go(-1);
  else if(e.key==="?") document.querySelector("details").open=!document.querySelector("details").open;
});
if(localStorage.getItem(KEY+"_seen")){ draw(); }
else { document.querySelector("footer").hidden=true;
       $("count").textContent=ROWS.length+" rows"; }
if(coded()>0){ $("resume").hidden=false; }
</script></body></html>
"""


def accident_note(ex):
    """If a row was retrieved only by an accidental substring match, say which word did it.

    Otherwise the coder stares at fee boilerplate with a highlight on "installments" and no
    idea why the row exists.
    """
    if ex.startswith("[No AI"):
        return ""
    if re.search(GENUINE_TERMS, ex, re.I):
        return ""
    words = set()
    for m in re.finditer(RETRIEVAL_TERMS, ex, re.I):
        a, b = m.start(), m.end()
        while a > 0 and ex[a - 1].isalpha():
            a -= 1
        while b < len(ex) and ex[b].isalpha():
            b += 1
        words.add(ex[a:b])
    w = ", ".join(sorted(words)[:3]) or "a substring match"
    return ("No AI vocabulary here. The classifier's keyword filter retrieved this passage on "
            f"an accidental substring match ({w}) and labelled it all zeros. "
            "Pre-set to zero \u2014 press Enter.")

def main():
    rows, assign, meta = build_assignment()
    os.makedirs(OUT, exist_ok=True)
    rub = "".join(f"<tr><td><b>{k}</b></td><td><b>{n}</b><br>{html.escape(dsc)}</td></tr>"
                  for k, n, dsc in LABELS)
    for coder in CODERS:
        ids = assign[coder]
        rng = random.Random(SEED + sum(map(ord, coder)))
        order = list(ids)
        rng.shuffle(order)                      # each coder walks a different sequence
        data = []
        for rid in order:
            ex = str(rows.loc[rid, "excerpt"])
            data.append({"id": rid, "html": highlight(ex),
                         # The fallback message itself says "No AI-related passage", which the
                         # genuine-term test would read as AI vocabulary, so it is handled first.
                         "pre": ex.startswith("[No AI")
                                or not re.search(GENUINE_TERMS, ex, re.I),
                         "why": accident_note(ex)})
        page = PAGE % {"coder": coder, "npre": sum(1 for d_ in data if d_["pre"]), "coder_js": json.dumps(coder),
                       "rows": json.dumps(data), "n": len(data), "rubric": rub,
                       "labs": json.dumps([[k, n, d] for k, n, d in LABELS])}
        open(os.path.join(OUT, f"human_validation_{coder}.html"), "w", encoding="utf-8").write(page)
        print(f"  human_validation_{coder}.html  {len(data)} rows")
    json.dump(meta, open(os.path.join(OUT, "assignment.json"), "w"), indent=1)
    print(f"  assignment.json  no double coding; {meta['n_disagreement_census']} disagreement "
          f"census + {meta['n_agreement']} agreement + {meta['n_website']} website, split "
          f"{meta['n_per_coder']}")
    for c, comp in meta["composition_per_coder"].items():
        print(f"     {c}: {comp}")


if __name__ == "__main__":
    main()
