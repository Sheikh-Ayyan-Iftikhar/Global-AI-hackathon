"""main.py - FastAPI app. Run: uvicorn main:app --reload --port 8000"""
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
import storage as st
from engine import resolve_current

app = FastAPI(title="FreshGuard AI", version="1.0.0", description="Stale-Answer Detector for AI Applications")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:8000"],
                   allow_methods=["*"], allow_headers=["*"])
STORE = st.STORE

# ───────── schemas ─────────
class AnalyzeRequest(BaseModel):
    question: str = Field("", max_length=2000)
    answer: str = Field(..., max_length=8000)
    source_ids: Optional[list[str]] = None
    context: str = Field("", max_length=8000)
    @field_validator("answer")
    @classmethod
    def not_empty(cls, v):
        if not v.strip(): raise ValueError("Answer must not be empty")
        return v

class UrlRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)

class ConflictRequest(BaseModel):
    enabled: bool = True

class Weights(BaseModel):
    temporal: float = Field(0.35, ge=0, le=1)
    contradiction: float = Field(0.40, ge=0, le=1)
    age: float = Field(0.25, ge=0, le=1)

class Thresholds(BaseModel):
    fresh: int = Field(80, ge=1, le=100)
    review: int = Field(60, ge=1, le=100)
    stale: int = Field(30, ge=1, le=100)

class SettingsModel(BaseModel):
    weights: Weights = Weights()
    thresholds: Thresholds = Thresholds()
    @model_validator(mode="after")
    def check(self):
        w = self.weights
        if abs(w.temporal + w.contradiction + w.age - 1) > 0.01: raise ValueError("Weights must sum to 1.0")
        t = self.thresholds
        if not (t.fresh > t.review > t.stale): raise ValueError("Thresholds must satisfy fresh > review > stale")
        return self

def _src_or_404(sid):
    s = STORE.sources.get(sid)
    if not s: raise HTTPException(404, f"Source '{sid}' not found")
    return s

# ───────── routes ─────────
@app.get("/health")
def health():
    return {"status": "ok", "sources": len(STORE.sources), "analyses": len(STORE.results),
            "llm_configured": bool(os.getenv("LLM_API_KEY"))}

@app.post("/api/v1/analyze")
def analyze_route(req: AnalyzeRequest):
    try:
        return st.analyze_and_record(STORE, req.question, req.answer, req.source_ids, req.context)
    except LookupError as e: raise HTTPException(404, str(e))
    except ValueError as e: raise HTTPException(422, str(e))

@app.post("/api/v1/sources/upload", status_code=201)
async def upload(file: UploadFile = File(...), group: Optional[str] = Form(None), version: Optional[int] = Form(None)):
    data = await file.read()
    try: return st.public(st.ingest_file(STORE, file.filename or "upload", data, group, version))
    except st.IngestError as e: raise HTTPException(e.status, str(e))

@app.post("/api/v1/sources/url", status_code=201)
def add_url(req: UrlRequest):
    try: return st.public(st.ingest_url(STORE, req.url.strip()))
    except st.IngestError as e: raise HTTPException(e.status, str(e))

@app.get("/api/v1/sources")
def list_sources():
    srcs = list(STORE.sources.values()); cur = resolve_current(srcs)
    return [st.public(s, cur) for s in srcs]

@app.get("/api/v1/sources/{sid}")
def get_source(sid: str):
    s = _src_or_404(sid)
    return st.public(s, resolve_current(list(STORE.sources.values())), with_text=True)

@app.post("/api/v1/sources/{sid}/reprocess")
def reprocess(sid: str):
    _src_or_404(sid)
    try: return st.public(st.reprocess(STORE, sid))
    except st.IngestError as e: raise HTTPException(e.status, str(e))

@app.delete("/api/v1/sources/{sid}")
def delete_source(sid: str):
    _src_or_404(sid); st.remove_source(STORE, sid)
    return {"deleted": sid}

@app.get("/api/v1/answers")
def answers():
    return [{"id": r.id, "question": r.question, "answer": r.answer, "status": r.status, "score": r.overall_score,
             "band": r.band, "created_at": r.created_at} for r in reversed(STORE.results)]

@app.get("/api/v1/detections")
def detections():
    return [r.model_dump() for r in reversed(STORE.results)]

@app.get("/api/v1/analytics/overview")
def analytics(): return st.overview(STORE)

@app.get("/api/v1/settings")
def get_settings():
    return {**STORE.settings, "llm": {"configured": bool(os.getenv("LLM_API_KEY")), "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")}}

@app.put("/api/v1/settings")
def put_settings(s: SettingsModel):
    STORE.settings = s.model_dump(); return STORE.settings

@app.get("/api/v1/demo/scenarios")
def scenarios(): return st.SCENARIOS

@app.post("/api/v1/demo/seed")
def seed():
    st.seed_demo(STORE); return {"sources": len(STORE.sources), "message": "Demo data loaded (temporary, in-memory)"}

@app.post("/api/v1/demo/reset")
def reset():
    STORE.reset(); return {"message": "State cleared"}

@app.post("/api/v1/demo/conflict")
def conflict(req: ConflictRequest):
    if not STORE.sources: st.seed_demo(STORE)
    st.set_conflict(STORE, req.enabled); return {"conflict": req.enabled}

@app.post("/api/v1/demo/simulate-update")
def simulate(): return st.simulate_update(STORE)

# UI (must be mounted last)
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="ui")