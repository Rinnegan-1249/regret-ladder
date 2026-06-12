"""Regret Ladder interactive website.

Run from the repo root:
    uvicorn web.app:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from web import kuhn_engine, rps_engine, training_stream
from web.bots import list_kuhn_bots
from web.rps_engine import SeatSpec

ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent

app = FastAPI(title="Regret Ladder")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
app.mount("/papers", StaticFiles(directory=ROOT / "Research_Papers"), name="papers")
app.mount("/figures", StaticFiles(directory=ROOT / "results" / "figures"), name="figures")
templates = Jinja2Templates(directory=WEB / "templates")

# Cache-busting version for our own static assets: newest mtime under
# web/static, computed at startup. Templates append ?v={{ v }} so browsers
# always fetch fresh JS/CSS after a change without needing a hard refresh.
_STATIC_VERSION = str(int(max(
    p.stat().st_mtime for p in (WEB / "static").rglob("*") if p.is_file()
)))
templates.env.globals["v"] = _STATIC_VERSION


# ---------- pages ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"page": "home"})


@app.get("/rps", response_class=HTMLResponse)
def rps_page(request: Request):
    return templates.TemplateResponse(request, "rps.html", {"page": "rps"})


@app.get("/kuhn", response_class=HTMLResponse)
def kuhn_page(request: Request):
    return templates.TemplateResponse(
        request, "kuhn.html", {"page": "kuhn", "bots": list_kuhn_bots()}
    )


@app.get("/results", response_class=HTMLResponse)
def results_page(request: Request):
    return templates.TemplateResponse(request, "results.html", {"page": "results"})


@app.get("/references", response_class=HTMLResponse)
def references_page(request: Request):
    return templates.TemplateResponse(request, "references.html", {"page": "references"})


# ---------- bot listing ----------

@app.get("/api/bots")
def api_bots():
    return {"kuhn": list_kuhn_bots()}


# ---------- RPS API ----------

class RpsSeatModel(BaseModel):
    kind: str
    dist: list[float] | None = None


class RpsNewModel(BaseModel):
    p1: RpsSeatModel
    p2: RpsSeatModel
    rounds: int = 10
    seed: int = 0


class RpsPlayModel(BaseModel):
    p1_action: int | None = None
    p2_action: int | None = None


@app.post("/api/rps/new")
def rps_new(body: RpsNewModel):
    try:
        match = rps_engine.new_match(
            SeatSpec(body.p1.kind, body.p1.dist),
            SeatSpec(body.p2.kind, body.p2.dist),
            rounds=body.rounds,
            seed=body.seed,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return match.summary()


@app.post("/api/rps/{match_id}/play")
def rps_play(match_id: str, body: RpsPlayModel):
    try:
        match = rps_engine.get_match(match_id)
        row = match.play_round(body.p1_action, body.p2_action)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"round": row, "summary": match.summary()}


@app.post("/api/rps/{match_id}/auto")
def rps_auto(match_id: str):
    try:
        match = rps_engine.get_match(match_id)
        rows = match.auto_run()
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"rounds": rows, "summary": match.summary()}


# ---------- Kuhn API ----------

class KuhnNewModel(BaseModel):
    p1: str
    p2: str
    hands: int = 10
    seed: int = 0


class KuhnActModel(BaseModel):
    action: int


@app.post("/api/kuhn/new")
def kuhn_new(body: KuhnNewModel):
    try:
        match = kuhn_engine.new_match(body.p1, body.p2, hands=body.hands, seed=body.seed)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return match.view()


@app.get("/api/kuhn/{match_id}/state")
def kuhn_state(match_id: str):
    try:
        return kuhn_engine.get_match(match_id).view()
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/api/kuhn/{match_id}/act")
def kuhn_act(match_id: str, body: KuhnActModel):
    try:
        return kuhn_engine.get_match(match_id).act(body.action)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/kuhn/{match_id}/auto")
def kuhn_auto(match_id: str):
    try:
        return kuhn_engine.get_match(match_id).auto_run()
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------- live training (SSE) ----------

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@app.get("/api/train/rps/stream")
def train_rps(iterations: int = 10_000, seed: int = 0):
    return StreamingResponse(
        training_stream.rps_stream(iterations, seed),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@app.get("/api/train/kuhn/stream")
def train_kuhn(algo: str = "cfr", iterations: int = 1_000, seed: int = 0):
    if algo not in training_stream.KUHN_ALGOS:
        raise HTTPException(400, f"Unknown algorithm: {algo}")
    return StreamingResponse(
        training_stream.kuhn_stream(algo, iterations, seed),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
