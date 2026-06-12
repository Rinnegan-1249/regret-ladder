import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

import web.bots as bots
from web.app import app

client = TestClient(app)


# ---------- pages ----------

@pytest.mark.parametrize("path,marker", [
    ("/", "Regret Ladder"),
    ("/games", "Kuhn"),
    ("/foundations", "information sets"),
    ("/regret", "Counterfactual"),
    ("/rps", "Rock"),
    ("/kuhn", "Kuhn"),
    ("/results", "Results"),
    ("/references", "Zinkevich"),
])
def test_pages_render(path, marker):
    resp = client.get(path)
    assert resp.status_code == 200
    assert marker in resp.text


def test_bot_listing():
    resp = client.get("/api/bots")
    assert resp.status_code == 200
    ids = {b["id"] for b in resp.json()["kuhn"]}
    assert {"random", "always_call", "always_fold", "rule_based", "ev_heuristic",
            "cfr", "cfr_plus", "os_mccfr", "es_mccfr"} <= ids


# ---------- RPS ----------

def test_rps_human_vs_frozen_bot_round():
    new = client.post("/api/rps/new", json={
        "p1": {"kind": "human"}, "p2": {"kind": "rm_frozen"}, "rounds": 3,
    }).json()
    resp = client.post(f"/api/rps/{new['match_id']}/play", json={"p1_action": 0})
    assert resp.status_code == 200
    row = resp.json()["round"]
    assert row["p1_action"] == 0
    assert row["p2_action"] in (0, 1, 2)
    assert row["p1_payoff"] in (-1.0, 0.0, 1.0)


def test_rps_adaptive_bot_learns_from_realized_play():
    new = client.post("/api/rps/new", json={
        "p1": {"kind": "human"}, "p2": {"kind": "rm_adaptive"}, "rounds": 60,
    }).json()
    mid = new["match_id"]
    # Human spams rock; the adaptive bot should shift its strategy toward paper.
    last = None
    for _ in range(60):
        last = client.post(f"/api/rps/{mid}/play", json={"p1_action": 0}).json()
    strategy = last["round"]["p2_adaptive_strategy"]
    assert strategy[1] == max(strategy), f"expected paper-heavy strategy, got {strategy}"


def test_rps_distribution_validation():
    resp = client.post("/api/rps/new", json={
        "p1": {"kind": "distribution", "dist": [0.9, 0.5, 0.1]},
        "p2": {"kind": "rm_frozen"}, "rounds": 5,
    })
    assert resp.status_code == 400


def test_rps_bot_vs_bot_auto():
    new = client.post("/api/rps/new", json={
        "p1": {"kind": "rm_frozen"}, "p2": {"kind": "distribution", "dist": [1.0, 0.0, 0.0]},
        "rounds": 50,
    }).json()
    resp = client.post(f"/api/rps/{new['match_id']}/auto")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rounds"]) == 50
    assert data["summary"]["finished"] is True


# ---------- Kuhn ----------

@pytest.fixture()
def fast_cfr_bots(monkeypatch, tmp_path):
    """Tiny training budgets + isolated cache for CFR-family bots in tests."""
    monkeypatch.setattr(bots, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(bots, "KUHN_CFR_BOTS", {
        "cfr": ("Vanilla CFR (test)", "cfr", 50, None),
        "cfr_plus": ("CFR+ (test)", "cfr_plus", 50, None),
        "os_mccfr": ("OS-MCCFR (test)", "os_mccfr", 200, 0),
        "es_mccfr": ("ES-MCCFR (test)", "es_mccfr", 200, 0),
    })


def test_kuhn_human_vs_bot_hides_opponent_card():
    new = client.post("/api/kuhn/new", json={"p1": "human", "p2": "always_call", "hands": 2}).json()
    assert new["your_card"] in ("Jack", "Queen", "King")
    assert "p2" not in json.dumps(new.get("last_hand") or {})
    # Play hands to completion with legal actions only.
    mid = new["match_id"]
    view = new
    while not view["finished"]:
        if view.get("to_act"):
            action = view["legal_actions"][0]["action"]
            view = client.post(f"/api/kuhn/{mid}/act", json={"action": action}).json()
        else:
            view = client.get(f"/api/kuhn/{mid}/state").json()
    assert view["hands_played"] == 2


def test_kuhn_illegal_inputs_rejected():
    resp = client.post("/api/kuhn/new", json={"p1": "human", "p2": "human", "hands": 2})
    assert resp.status_code == 400  # two humans would leak cards
    new = client.post("/api/kuhn/new", json={"p1": "human", "p2": "random", "hands": 2}).json()
    resp = client.post(f"/api/kuhn/{new['match_id']}/act", json={"action": 7})
    assert resp.status_code == 400


def test_kuhn_bot_vs_bot_auto_with_cfr_bot(fast_cfr_bots):
    new = client.post("/api/kuhn/new", json={"p1": "cfr", "p2": "always_fold", "hands": 300}).json()
    res = client.post(f"/api/kuhn/{new['match_id']}/auto").json()
    assert res["hands"] == 300
    # CFR should beat always-fold decisively.
    assert res["p1_mean_payoff"] > 0.2
    assert res["ci_low"] <= res["p1_mean_payoff"] <= res["ci_high"]


# ---------- training streams ----------

def _sse_events(resp_text):
    return [json.loads(line[6:]) for line in resp_text.splitlines() if line.startswith("data: ")]


def test_rps_training_stream():
    resp = client.get("/api/train/rps/stream?iterations=500&seed=0")
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done"
    cps = [e for e in events if e["type"] == "checkpoint"]
    assert len(cps) >= 1
    assert np.isclose(sum(cps[-1]["p1_avg"]), 1.0)


@pytest.mark.parametrize("algo", ["cfr", "cfr_plus", "os_mccfr", "es_mccfr"])
def test_kuhn_training_stream(algo):
    resp = client.get(f"/api/train/kuhn/stream?algo={algo}&iterations=30&seed=0")
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    assert events[-1]["type"] == "done"
    cps = [e for e in events if e["type"] == "checkpoint"]
    assert len(cps) >= 1
    last = cps[-1]
    assert last["exploitability"] >= 0
    assert set(last["bet_probs"].keys()) == {"p1", "p2"}


def test_kuhn_training_stream_rejects_unknown_algo():
    resp = client.get("/api/train/kuhn/stream?algo=nope&iterations=10")
    assert resp.status_code == 400
