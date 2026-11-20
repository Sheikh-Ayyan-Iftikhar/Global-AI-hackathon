"""storage.py - in-memory store, document ingestion, demo data, knowledge-update simulation. NO database."""
from __future__ import annotations
import hashlib, io, re, uuid, socket, ipaddress
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from engine import (split_sentences, analyze, resolve_current, diff_facts, DEFAULT_SETTINGS)

UPLOAD_DIR = Path(__file__).parent / "uploads"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {".pdf", ".txt", ".docx"}

class IngestError(Exception):
    def __init__(self, msg, status=422):
        super().__init__(msg); self.status = status

class Store:
    def __init__(self): self.reset()
    def reset(self):
        self.sources: dict[str, dict] = {}
        self.results: list = []          # AnalysisResult objects (temporary demo state)
        self.settings = deepcopy(DEFAULT_SETTINGS)

STORE = Store()

# ───────────── ingestion ─────────────
def normalize_text(t: str) -> str:
    t = t.replace("\r", "\n").replace("\x00", "")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()

def chunk_text(text: str, max_len: int = 300) -> list[str]:
    out = []
    for s in split_sentences(text):
        while len(s) > max_len:
            cut = s.rfind(" ", 0, max_len) or max_len
            out.append(s[:cut].strip()); s = s[cut:].strip()
        if s: out.append(s)
    return out

def parse_bytes(ext: str, data: bytes) -> str:
    ext = ext.lower()
    if ext == ".txt":
        return data.decode("utf-8", errors="replace")
    if ext == ".pdf":
        import fitz  # PyMuPDF
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(p.get_text() for p in doc)
    if ext == ".docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for tb in d.tables:
            for row in tb.rows:
                parts.append(" ".join(c.text for c in row.cells))
        return "\n".join(parts)
    raise IngestError(f"Unsupported file type: {ext}", 415)

def _safe_url(url: str):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise IngestError("Only valid http(s) URLs are allowed", 422)
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise IngestError("Private/local addresses are blocked", 422)
    except socket.gaierror:
        raise IngestError("Could not resolve host", 422)

def fetch_url(url: str) -> str:
    import httpx
    from bs4 import BeautifulSoup
    _safe_url(url)
    try:
        r = httpx.get(url, timeout=15, follow_redirects=False, headers={"User-Agent": "FreshGuardAI/1.0"})
        r.raise_for_status()
    except Exception as e:
        raise IngestError(f"Could not fetch URL: {e}", 502)
    if len(r.content) > MAX_BYTES:
        raise IngestError("Page too large", 413)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    return soup.get_text("\n")

def infer_group(name: str):
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    m = re.search(r"[_\-\s]?(?:v|rev)(\d+)$", stem, re.I)
    return (stem[:m.start()].lower(), int(m.group(1))) if m else (stem.lower(), 1)

def _apply_text(s: dict, text: str):
    text = normalize_text(text)
    if not text:
        raise IngestError("No extractable text found in the source", 422)
    s["text"], s["chunks"] = text, chunk_text(text)
    s["hash"] = hashlib.sha256(text.encode()).hexdigest()
    s["size"] = len(text)

def make_source(store, name, stype, text, group=None, version=None, days_ago=0, path=None, url=None):
    g, v = infer_group(name)
    now = datetime.now(timezone.utc)
    s = {"id": uuid.uuid4().hex[:8], "name": name, "type": stype, "status": "ready", "error": None,
         "group": (group or g), "version": version or v, "active": True, "path": path, "url": url,
         "created_at": now.isoformat(), "effective_date": (now - timedelta(days=days_ago)).isoformat()}
    _apply_text(s, text)
    store.sources[s["id"]] = s
    return s

def ingest_file(store, filename, data, group=None, version=None):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED: raise IngestError(f"Unsupported file type '{ext}'. Allowed: PDF, TXT, DOCX", 415)
    if len(data) > MAX_BYTES: raise IngestError("File too large (max 10 MB)", 413)
    if not data: raise IngestError("File is empty", 422)
    try:
        text = parse_bytes(ext, data)
    except IngestError: raise
    except Exception as e:
        raise IngestError(f"Could not read file: {e}", 422)
    UPLOAD_DIR.mkdir(exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
    path = UPLOAD_DIR / f"{uuid.uuid4().hex[:6]}_{safe}"
    path.write_bytes(data)
    return make_source(store, Path(filename).name, ext[1:], text, group, version, path=str(path))

def ingest_url(store, url):
    p = urlparse(url)
    return make_source(store, f"{p.hostname}{p.path}".rstrip("/"), "url", fetch_url(url), group=f"{p.hostname}{p.path}".lower(), url=url)

def reprocess(store, sid):
    s = store.sources.get(sid)
    if not s: raise KeyError(sid)
    try:
        if s["type"] == "url": text = fetch_url(s["url"])
        elif s.get("path") and Path(s["path"]).exists(): text = parse_bytes(Path(s["path"]).suffix, Path(s["path"]).read_bytes())
        else: text = s["text"]
        _apply_text(s, text); s["status"], s["error"] = "ready", None
    except IngestError as e:
        s["status"], s["error"] = "failed", str(e); raise
    return s

def remove_source(store, sid):
    s = store.sources.pop(sid, None)
    if not s: raise KeyError(sid)
    if s.get("path"): Path(s["path"]).unlink(missing_ok=True)

def public(s, current_ids=None, with_text=False):
    d = {k: s[k] for k in ("id", "name", "type", "status", "error", "group", "version", "active", "created_at", "effective_date", "hash", "size")}
    d["chunk_count"], d["char_count"] = len(s["chunks"]), len(s["text"])
    if current_ids is not None: d["current"] = s["id"] in current_ids
    if with_text: d["text"], d["chunks"] = s["text"], s["chunks"]
    return d

# ───────────── analysis + analytics ─────────────
def analyze_and_record(store, question, answer, source_ids=None, context="", use_llm=True):
    srcs = list(store.sources.values())
    if source_ids:
        missing = [i for i in source_ids if i not in store.sources]
        if missing: raise LookupError(f"Unknown source ids: {missing}")
        srcs = [store.sources[i] for i in source_ids]
    res = analyze(question, answer, srcs, store.settings, context, use_llm)
    store.results.append(res)
    return res

def overview(store):
    r, srcs = store.results, list(store.sources.values())
    scores = [x.overall_score for x in r if x.overall_score is not None]
    cur = resolve_current(srcs)
    n = lambda s: sum(1 for x in r if x.status == s)
    return {
        "total": len(r), "fresh": n("FRESH"), "stale": n("STALE"), "unverified": n("UNVERIFIED"),
        "conflict": n("CONFLICT"), "review": n("REVIEW"),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "risk_distribution": dict(Counter(x.risk_level for x in r)),
        "band_distribution": dict(Counter(x.band for x in r)),
        "category_counts": dict(Counter(c.category for x in r for c in x.claims)),
        "trend": [{"t": x.created_at, "score": x.overall_score, "status": x.status} for x in r if x.overall_score is not None],
        "recent": [x.model_dump() for x in reversed(r[-5:])],
        "sources": {"total": len(srcs), "ready": sum(1 for s in srcs if s["status"] == "ready"),
                    "failed": sum(1 for s in srcs if s["status"] == "failed"), "current": len(cur),
                    "superseded": len(srcs) - len(cur), "chunks": sum(len(s["chunks"]) for s in srcs),
                    "by_type": dict(Counter(s["type"] for s in srcs))},
    }

# ───────────── demo data ─────────────
DEMO_DOCS = {  # name: (text, days_ago)
    "pricing_v1.txt": ("Premium Plan: $99/month.\nProfessional Plan: $199/month.", 400),
    "pricing_v2.txt": ("Premium Plan: $149/month.\nProfessional Plan: $249/month.", 20),
    "api_docs_rev1.txt": ("Current API version is v2.\nRate limit is 500 requests per minute.\nAuthentication uses Bearer tokens.", 380),
    "api_docs_rev2.txt": ("Current API version is v3.\nRate limit is 1000 requests per minute.\nAuthentication uses Bearer tokens.", 15),
    "company_policy.txt": ("Company was founded in 2018.\nRefunds are available within 30 days of purchase.\nSupport email is support@freshguard.example.", 60),
    "product_docs.txt": ("The Premium plan includes priority email support and 50 GB of storage.\nThe Professional plan includes phone support and 500 GB of storage.", 45),
    "sales_deck_2025.txt": ("Premium Plan: $129/month.", 90),   # conflicting doc
}
BASE_DOCS = ["pricing_v1.txt", "api_docs_rev1.txt", "company_policy.txt", "product_docs.txt"]
UPDATES = [("pricing_v1.txt", "pricing_v2.txt"), ("api_docs_rev1.txt", "api_docs_rev2.txt")]
CONFLICT_DOC = "sales_deck_2025.txt"

SCENARIOS = [
    {"id": 1, "title": "Stale price", "expected": "STALE", "question": "What is the current premium plan price?", "answer": "Our Premium plan costs $99 per month."},
    {"id": 2, "title": "Fresh price", "expected": "FRESH", "question": "What is the current premium plan price?", "answer": "Our Premium plan costs $149 per month."},
    {"id": 3, "title": "Unverified", "expected": "UNVERIFIED", "question": "What does the Premium plan include?", "answer": "Our Premium plan includes unlimited AI requests."},
    {"id": 4, "title": "Conflict", "expected": "CONFLICT", "question": "What is the current premium plan price?", "answer": "Our Premium plan costs $149 per month.", "needs_conflict": True},
    {"id": 5, "title": "Outdated version", "expected": "STALE", "question": "What is the latest API version?", "answer": "The latest API version is v2."},
]
SIM_ANSWERS = [
    ("What is the current premium plan price?", "Our Premium plan costs $99 per month."),
    ("What does the Professional plan cost?", "The Professional plan costs $199 per month."),
    ("What is the latest API version?", "The latest API version is v2."),
    ("When was the company founded?", "Our company was founded in 2018."),
]

def _add_demo(store, name):
    text, days = DEMO_DOCS[name]
    return make_source(store, name, "txt", text, days_ago=days)

def seed_demo(store, with_updates=True):
    store.reset()
    for n in BASE_DOCS: _add_demo(store, n)
    if with_updates:
        for _, n in UPDATES: _add_demo(store, n)
    return store

def set_conflict(store, enabled: bool):
    existing = [s for s in store.sources.values() if s["name"] == CONFLICT_DOC]
    if enabled and not existing: _add_demo(store, CONFLICT_DOC)
    if not enabled:
        for s in existing: store.sources.pop(s["id"], None)

def simulate_update(store):
    """Old source -> new source -> hash compare -> changed facts -> revalidate answers -> stale alerts (all real computation)."""
    names = {s["name"] for s in store.sources.values()}
    if "pricing_v1.txt" not in names:
        seed_demo(store, with_updates=False)
    else:
        for s in [s for s in store.sources.values() if s["name"] in {u[1] for u in UPDATES} | {CONFLICT_DOC}]:
            store.sources.pop(s["id"], None)
    old_by_name = {s["name"]: s for s in store.sources.values()}
    pairs, seen = [], set()
    for r in store.results:
        if (r.question, r.answer) not in seen: seen.add((r.question, r.answer)); pairs.append((r.question, r.answer))
    for qa in SIM_ANSWERS:
        if qa not in seen: seen.add(qa); pairs.append(qa)
    old_list = list(store.sources.values())
    before = [analyze(q, a, old_list, store.settings, use_llm=False) for q, a in pairs]
    changes = []
    for old_n, new_n in UPDATES:
        o = old_by_name[old_n]; n = _add_demo(store, new_n)
        changes.append({"group": o["group"], "old_name": old_n, "new_name": new_n, "old_hash": o["hash"], "new_hash": n["hash"],
                        "changed": o["hash"] != n["hash"], "changed_facts": diff_facts(o["text"], n["text"])})
    new_list = list(store.sources.values())
    revalidated, alerts = [], []
    for (q, a), b in zip(pairs, before):
        af = analyze(q, a, new_list, store.settings, use_llm=False)
        store.results.append(af)
        alert = ("NEW_STALE" if af.status == "STALE" and b.status != "STALE" else
                 "RECOVERED" if b.status == "STALE" and af.status == "FRESH" else
                 "CHANGED" if af.status != b.status else None)
        if alert == "NEW_STALE":
            alerts.append(f"STALE ALERT: \"{a}\" is now outdated - {af.claims[0].explanation}")
        revalidated.append({"question": q, "answer": a, "alert": alert,
                            "before": {"status": b.status, "score": b.overall_score},
                            "after": {"status": af.status, "score": af.overall_score},
                            "detail": af.claims[0].model_dump()})
    return {"changes": changes, "revalidated": revalidated, "alerts": alerts,
            "summary": {"documents_changed": sum(c["changed"] for c in changes),
                        "facts_changed": sum(len(c["changed_facts"]) for c in changes),
                        "answers_revalidated": len(pairs), "new_stale": len(alerts)}}