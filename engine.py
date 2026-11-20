"""engine.py - FreshGuard AI detection engine.
Sections: claim_extractor, claim_classifier, temporal_analyzer, evidence_retriever,
contradiction_detector, freshness_scorer, stale_detector, explanation_generator."""
from __future__ import annotations
import os, re, uuid, json
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

DEFAULT_SETTINGS = {
    "weights": {"temporal": 0.35, "contradiction": 0.40, "age": 0.25},
    "thresholds": {"fresh": 80, "review": 60, "stale": 30},
}

# ───────────────────────── models ─────────────────────────
class Evidence(BaseModel):
    source_id: str
    source_name: str
    text: str
    similarity: float
    current: bool = True            # False = superseded / archived version
    effective_date: Optional[str] = None

class ClaimResult(BaseModel):
    text: str
    category: str
    sensitivity: str
    markers: list[str] = Field(default_factory=list)
    temporal_risk: float
    contradiction_severity: float
    evidence_age_risk: float
    score: Optional[float] = None
    band: str
    status: str                      # FRESH | STALE | CONFLICT | UNVERIFIED
    old_value: Optional[str] = None
    current_value: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)
    explanation: str
    action: str

class AnalysisResult(BaseModel):
    id: str
    question: str
    answer: str
    created_at: str
    overall_score: Optional[float] = None
    band: str
    status: str                      # FRESH | REVIEW | STALE | CONFLICT | UNVERIFIED
    risk_level: str
    coverage: float
    claims: list[ClaimResult]
    summary: str
    recommended_action: str
    notes: list[str] = Field(default_factory=list)
    llm_used: bool = False

# ───────────────────────── text utils ─────────────────────────
def split_sentences(text: str) -> list[str]:
    out = []
    for line in re.split(r"[\r\n]+", text):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line).strip()
        if not line:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", line):
            s = s.strip()
            if s:
                out.append(s)
    return out

STOP = set("""a an the our we us is are was were be been am it its this that these those of in on at to for from by with and or as per
month months monthly year years yearly annual cost costs price prices priced pricing plan plans currently current latest newest now today
version versions include includes included including has have had can will would available offer offers offered starts start about""".split())

def _norm(w: str) -> str:
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w

def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]{2,}", text.lower())

def subject_tokens(text: str) -> set[str]:
    return {_norm(w) for w in tokens(text) if w not in STOP and _norm(w) not in STOP}

def _subj_ok(cs: set, chunk_text: str, thr: float) -> bool:
    return bool(cs) and len(cs & subject_tokens(chunk_text)) / len(cs) >= thr

# ───────────────────────── claim_extractor ─────────────────────────
def extract_claims(answer: str) -> list[str]:
    claims, seen = [], set()
    for s in split_sentences(answer):
        for part in re.split(r";\s+", s):
            part = part.strip()
            if part.endswith("?") or len(part.split()) < 3:
                continue
            if part.lower() not in seen:
                seen.add(part.lower())
                claims.append(part)
    return claims

# ───────────────────────── claim_classifier ─────────────────────────
_RULES = [(c, re.compile(p, re.I)) for c, p in [
    ("Laws & Regulations", r"\b(law|laws|legal|regulation|regulations|gdpr|compliance|statute|tax|legislation)\b"),
    ("Current Events", r"\b(today|this week|this month|recently|breaking|news|election)\b"),
    ("Pricing", r"[$€£]|\b(price|pricing|cost|costs|fee|fees|subscription|per month|per year|usd)\b"),
    ("Software Versions", r"\bv\d+(?:\.\d+)*\b|\b(version|release|released|sdk)\b"),
    ("Contact Information", r"@|\b(phone|email|contact|address|hotline)\b"),
    ("Company Policies", r"\b(policy|policies|refund|refunds|terms|warranty|guarantee|privacy|return)\b"),
    ("Historical Facts", r"\b(founded|established|invented|born|originally|history)\b"),
    ("Product Specifications", r"\b(supports?|includes?|storage|gb|tb|mb|limit|features?|capacity|requests|users|specs?)\b"),
    ("Dates", r"\b(19|20)\d{2}\b|\b(january|february|march|april|may|june|july|august|september|october|november|december)\b|deadline|launch"),
]]

def classify_claim(claim: str) -> str:
    for cat, rx in _RULES:
        if rx.search(claim):
            return cat
    return "General Knowledge"

# ───────────────────────── temporal_analyzer ─────────────────────────
SENS = {"Pricing": 85, "Software Versions": 80, "Laws & Regulations": 95, "Current Events": 90,
        "Contact Information": 60, "Company Policies": 55, "Product Specifications": 55,
        "Dates": 40, "Historical Facts": 10, "General Knowledge": 10}

def temporal_sensitivity(claim: str, category: str):
    base = SENS.get(category, 10)
    marks = [m.lower() for m in re.findall(r"\b(current|currently|latest|newest|now|today|recent|new)\b", claim, re.I)]
    return min(100, base + (10 if marks else 0)), marks

def sens_label(v: float) -> str:
    return "Very high" if v >= 90 else "High" if v >= 70 else "Medium" if v >= 45 else "Low"

# ───────────────────────── contradiction_detector (deterministic facts) ─────────────────────────
_CUR = {"$": "USD", "usd": "USD", "dollar": "USD", "dollars": "USD", "€": "EUR", "euro": "EUR", "euros": "EUR",
        "£": "GBP", "pkr": "PKR", "rs": "PKR"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PRICE_RE = re.compile(r"(?:(?P<c1>[$€£]|\b(?:USD|PKR|Rs)\b\.?)\s?(?P<n1>\d[\d,]*(?:\.\d+)?))|(?:(?<![\w.])(?P<n2>\d[\d,]*(?:\.\d+)?)\s?(?P<c2>USD|PKR|dollars?|euros?)\b)", re.I)
VER_RE = re.compile(r"\b(?:v|version\s*)(\d+(?:\.\d+){0,2})\b", re.I)
QTY_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s?(GB|TB|MB|users?|seats?|requests?|days?|percent|%)(?!\w)", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

def extract_facts(text: str) -> list[dict]:
    facts, t = [], text
    def mask(rx, fn):
        nonlocal t
        for m in rx.finditer(t):
            f = fn(m)
            if f:
                facts.append(f)
        t = rx.sub(lambda m: " " * len(m.group(0)), t)
    mask(EMAIL_RE, lambda m: {"type": "email", "value": m.group(0).lower(), "unit": "", "raw": m.group(0)})
    def price(m):
        cur = (m.group("c1") or m.group("c2")).lower().strip(".")
        num = float((m.group("n1") or m.group("n2")).replace(",", ""))
        return {"type": "price", "value": num, "unit": _CUR.get(cur, cur.upper()), "raw": m.group(0).strip()}
    mask(PRICE_RE, price)
    def ver(m):
        v = [int(x) for x in m.group(1).split(".")]
        while len(v) > 1 and v[-1] == 0:
            v.pop()
        return {"type": "version", "value": tuple(v), "unit": "", "raw": m.group(0).strip()}
    mask(VER_RE, ver)
    def qty(m):
        u = m.group(2).lower()
        u = "%" if u in ("%", "percent") else u.rstrip("s")
        return {"type": "quantity", "value": float(m.group(1).replace(",", "")), "unit": u, "raw": m.group(0).strip()}
    mask(QTY_RE, qty)
    mask(YEAR_RE, lambda m: {"type": "year", "value": int(m.group(0)), "unit": "", "raw": m.group(0)})
    return facts

def _key(f): return (f["type"], f["unit"], f["value"])

def _pick(efs, f):
    if f["type"] == "version":
        return max(efs, key=lambda e: e["value"])
    eq = [e for e in efs if _key(e) == _key(f)]
    return eq[0] if eq else efs[0]

def _mk_ev(sim, c, current=True):
    return Evidence(source_id=c["source_id"], source_name=c["source_name"], text=c["text"],
                    similarity=round(float(sim), 3), current=current, effective_date=c.get("effective_date"))

def _check_fact(f, cs, hits):
    per_group, archived = {}, []
    for sim, c in hits:
        if not _subj_ok(cs, c["text"], 0.5):
            continue
        efs = [e for e in extract_facts(c["text"]) if e["type"] == f["type"]]
        if not efs:
            continue
        ev = _pick(efs, f)
        if c["current"]:
            g = c["group"]
            if g not in per_group or sim > per_group[g][0]:
                per_group[g] = (sim, c, ev)
        else:
            archived.append((sim, c, ev))
    if not per_group:
        return {"verdict": "none"}
    cur = list(per_group.values())
    distinct = {}
    for _, _, e in cur:
        distinct.setdefault(_key(e), e)
    evid = [_mk_ev(s, c) for s, c, _ in cur]
    arch_hit = next(((s, c) for s, c, e in archived if _key(e) == _key(f)), None)
    if arch_hit:
        evid.append(_mk_ev(arch_hit[0], arch_hit[1], current=False))
    eff = cur[0][1].get("effective_date")
    if len(distinct) > 1:
        return {"verdict": "conflict", "old": f["raw"], "ev": evid, "sev": 70, "eff": eff, "kind": "sources disagree",
                "cur": " vs ".join(f'{e["raw"]} ({c["source_name"]})' for _, c, e in cur), "src": ", ".join(c["source_name"] for _, c, _ in cur)}
    s, c, e = cur[0]
    if _key(e) == _key(f):
        return {"verdict": "fresh", "old": f["raw"], "cur": e["raw"], "ev": evid, "sev": 0, "eff": eff, "src": c["source_name"], "kind": ""}
    kind = {"price": "price changed", "version": "outdated version" if f["type"] == "version" and f["value"] < e["value"] else "version mismatch",
            "year": "date/year changed", "quantity": "numeric value changed", "email": "contact changed"}.get(f["type"], "value changed")
    if f["type"] == "price" and f["value"] == e["value"]:
        kind = "currency mismatch"
    return {"verdict": "stale", "old": f["raw"], "cur": e["raw"], "ev": evid, "sev": 100, "eff": eff,
            "arch": bool(arch_hit), "src": c["source_name"], "kind": kind}

def _neg(t): return bool(re.search(r"\b(not|no|never|cannot|without)\b|n't", t))

def _check_text(claim, cs, hits):
    cand = [(s, c) for s, c in hits if s >= 0.25 and c["current"] and _subj_ok(cs, c["text"], 0.6)]
    if not cand:
        return {"verdict": "none"}
    s, c = cand[0]
    cl, ct = claim.lower(), c["text"].lower()
    contra = ("unlimited" in cl and "unlimited" not in ct and re.search(r"\b(limit|limited|capped|maximum|max|up to)\b", ct)) or (_neg(cl) != _neg(ct))
    base = {"ev": [_mk_ev(s, c)], "eff": c.get("effective_date"), "src": c["source_name"]}
    if contra:
        return {**base, "verdict": "stale", "old": claim, "cur": c["text"], "sev": 60, "arch": False, "kind": "textual contradiction"}
    return {**base, "verdict": "fresh", "old": None, "cur": c["text"], "sev": 0, "kind": ""}

def diff_facts(old: str, new: str) -> list[dict]:
    """Detect changed facts between two versions of a document (used by Knowledge Update simulation)."""
    ns = [(s, subject_tokens(s), extract_facts(s)) for s in split_sentences(new)]
    out = []
    for o in split_sentences(old):
        of, os_ = extract_facts(o), subject_tokens(o)
        if not of or not os_ or not ns:
            continue
        best = max(ns, key=lambda n: len(os_ & n[1]) / len(os_))
        if len(os_ & best[1]) / len(os_) < 0.5:
            continue
        if sorted(map(str, map(_key, of))) != sorted(map(str, map(_key, best[2]))):
            out.append({"subject": " ".join(sorted(os_)), "old": [f["raw"] for f in of], "new": [f["raw"] for f in best[2]],
                        "old_line": o, "new_line": best[0]})
    return out

# ───────────────────────── evidence_retriever ─────────────────────────
def retrieve(claim: str, chunks: list[dict], top_k: int = 12):
    if not chunks:
        return []
    texts = [c["text"] for c in chunks]
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer(tokenizer=lambda s: [_norm(w) for w in tokens(s)], token_pattern=None, lowercase=False)
        m = vec.fit_transform(texts + [claim])
        sims = cosine_similarity(m[-1], m[:-1])[0]
    except Exception:  # fallback: fuzzy keyword matching
        try:
            from rapidfuzz import fuzz
            sims = [fuzz.token_set_ratio(claim, t) / 100 for t in texts]
        except Exception:
            ct = subject_tokens(claim)
            sims = [len(ct & subject_tokens(t)) / max(1, len(ct)) for t in texts]
    ranked = sorted(zip(sims, chunks), key=lambda x: -x[0])
    return [(float(s), c) for s, c in ranked[:top_k] if s > 0]

# ───────────────────────── freshness_scorer ─────────────────────────
def _parse_date(s):
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def _age_component(eff, sens):
    days = max(0, (datetime.now(timezone.utc) - _parse_date(eff)).days) if eff else 0
    return min(100.0, days / 730 * 100) * sens / 100

def band_for(score: float, th: dict) -> str:
    return "FRESH" if score >= th["fresh"] else "REVIEW" if score >= th["review"] else "POTENTIALLY STALE" if score >= th["stale"] else "HIGH STALE RISK"

def score_claim(status, sens, sev, eff, in_archive, settings):
    """Freshness = 100 - (wT*T + wC*C + wE*E). Temporal risk is residual: it shrinks once verified by current evidence."""
    w = settings["weights"]
    if status == "FRESH":
        T, C, E = sens * 0.15, 0.0, _age_component(eff, sens) * 0.5
    elif status == "STALE":
        T, C, E = sens, sev, (100.0 if in_archive else 60.0)
    elif status == "CONFLICT":
        T, C, E = sens, sev, _age_component(eff, sens)
    else:
        return round(sens, 1), 0.0, 0.0, None   # UNVERIFIED: no score (missing evidence != stale)
    score = max(0.0, min(100.0, 100 - (w["temporal"] * T + w["contradiction"] * C + w["age"] * E)))
    return round(T, 1), round(C, 1), round(E, 1), round(score, 1)

# ───────────────────────── explanation_generator ─────────────────────────
def explain(status, r, category):
    if status == "STALE":
        arch = " The AI's value matches an older, superseded document." if r.get("arch") else ""
        return f"The answer says '{r.get('old')}' but the current source '{r.get('src')}' says '{r.get('cur')}' ({r.get('kind')}).{arch}"
    if status == "CONFLICT":
        return f"Active sources disagree for the same fact: {r.get('cur')}. FreshGuard cannot tell which is authoritative."
    if status == "FRESH":
        return f"Verified: matches current source '{r.get('src')}' ({r.get('cur')})."
    return f"No sufficiently relevant evidence found for this {category.lower()} claim. This is UNVERIFIED, not necessarily stale."

def recommend(status, r):
    if status == "STALE":
        return f"Replace '{r.get('old')}' with '{r.get('cur')}', then regenerate the answer and refresh any cached responses."
    if status == "CONFLICT":
        return "Decide which document is authoritative, archive or fix the other one, then re-run the check."
    if status == "FRESH":
        return "No action needed."
    return "Upload a source covering this claim or have a human verify it before publishing."

class _LLMOut(BaseModel):
    summary: str = Field(min_length=10, max_length=1200)

def llm_rewrite(summary: str, claims: list) -> Optional[str]:
    """Optional OpenAI-compatible call. Returns None on any failure -> deterministic template is used."""
    key = os.getenv("LLM_API_KEY")
    if not key:
        return None
    try:
        import httpx
        base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        facts = [{"claim": c.text, "status": c.status, "old": c.old_value, "current": c.current_value} for c in claims]
        prompt = ('Rewrite this freshness report summary in 2 clear sentences. Do not invent facts. '
                  'Reply ONLY with JSON {"summary": "..."}.\n' + summary + "\n" + json.dumps(facts))
        r = httpx.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"},
                       json={"model": os.getenv("LLM_MODEL", "gpt-4o-mini"), "temperature": 0,
                             "messages": [{"role": "user", "content": prompt}]}, timeout=15)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return _LLMOut.model_validate_json(re.search(r"\{.*\}", content, re.S).group(0)).summary
    except Exception:
        return None

# ───────────────────────── stale_detector ─────────────────────────
def resolve_current(sources: list[dict]) -> set[str]:
    """Within each document group (pricing_v1, pricing_v2 -> 'pricing') only the newest active version is current."""
    best = {}
    for s in sources:
        if not s.get("active", True) or s.get("status") != "ready":
            continue
        g = s.get("group") or s["id"]
        k = (s.get("version") or 1, s.get("created_at", ""))
        if g not in best or k > best[g][0]:
            best[g] = (k, s["id"])
    return {v[1] for v in best.values()}

def detect_claim(claim, chunks, settings) -> ClaimResult:
    category = classify_claim(claim)
    sens, markers = temporal_sensitivity(claim, category)
    facts, cs, hits = extract_facts(claim), subject_tokens(claim), retrieve(claim, chunks)
    r = {"verdict": "none"}
    if facts:
        vs = [v for v in (_check_fact(f, cs, hits) for f in facts) if v["verdict"] != "none"]
        if vs:
            r = min(vs, key=lambda v: {"stale": 0, "conflict": 1, "fresh": 2}[v["verdict"]])
    else:
        r = _check_text(claim, cs, hits)
    status = {"none": "UNVERIFIED", "fresh": "FRESH", "stale": "STALE", "conflict": "CONFLICT"}[r["verdict"]]
    T, C, E, score = score_claim(status, sens, r.get("sev", 0), r.get("eff"), r.get("arch", False), settings)
    band = band_for(score, settings["thresholds"]) if score is not None else "UNVERIFIED"
    return ClaimResult(text=claim, category=category, sensitivity=sens_label(sens), markers=markers,
                       temporal_risk=T, contradiction_severity=C, evidence_age_risk=E, score=score, band=band,
                       status=status, old_value=r.get("old"), current_value=r.get("cur"), evidence=r.get("ev", []),
                       explanation=explain(status, r, category), action=recommend(status, r))

def analyze(question: str, answer: str, sources: list[dict], settings: dict | None = None,
            context: str = "", use_llm: bool = True) -> AnalysisResult:
    settings = settings or DEFAULT_SETTINGS
    claims = extract_claims(answer)
    if not claims:
        raise ValueError("No factual claims could be extracted from the answer.")
    cur_ids = resolve_current(sources)
    chunks = [{"source_id": s["id"], "source_name": s["name"], "text": t, "current": s["id"] in cur_ids,
               "group": s.get("group") or s["id"], "effective_date": s.get("effective_date")}
              for s in sources if s.get("status") == "ready" for t in s["chunks"]]
    notes = []
    if context.strip():
        chunks += [{"source_id": "context", "source_name": "User context", "text": t, "current": True, "group": "__ctx__",
                    "effective_date": datetime.now(timezone.utc).isoformat()} for t in split_sentences(context)]
    if not chunks:
        notes.append("No knowledge sources available - every claim is UNVERIFIED.")
    res = [detect_claim(c, chunks, settings) for c in claims]
    th = settings["thresholds"]
    scored = [c.score for c in res if c.score is not None]
    coverage = round(100 * len(scored) / len(res), 1)
    overall = round(0.5 * sum(scored) / len(scored) + 0.5 * min(scored), 1) if scored else None
    st = [c.status for c in res]
    if "STALE" in st: status = "STALE"
    elif "CONFLICT" in st: status = "CONFLICT"
    elif not scored: status = "UNVERIFIED"
    elif "UNVERIFIED" in st: status = "REVIEW"
    else: status = "FRESH" if overall >= th["fresh"] else "REVIEW"
    band = band_for(overall, th) if overall is not None else "N/A"
    risk = ("Critical" if overall is not None and overall < th["stale"] else "High") if status in ("STALE", "CONFLICT") else \
           "Medium" if status in ("UNVERIFIED", "REVIEW") else "Low"
    n = lambda s: st.count(s)
    summary = (f"{len(res)} claim(s) analyzed: {n('STALE')} stale, {n('CONFLICT')} conflicting, {n('FRESH')} verified fresh, "
               f"{n('UNVERIFIED')} unverified. Evidence coverage {coverage}%.")
    llm = llm_rewrite(summary, res) if use_llm else None
    first = next((c for c in res if c.status in ("STALE", "CONFLICT")), None) or next((c for c in res if c.status == "UNVERIFIED"), None) or res[0]
    return AnalysisResult(id=uuid.uuid4().hex[:10], question=question, answer=answer,
                          created_at=datetime.now(timezone.utc).isoformat(), overall_score=overall, band=band, status=status,
                          risk_level=risk, coverage=coverage, claims=res, summary=llm or summary,
                          recommended_action=first.action, notes=notes, llm_used=bool(llm))